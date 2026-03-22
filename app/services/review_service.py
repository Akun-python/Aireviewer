from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import asdict, dataclass, field
from datetime import datetime
import io
import os
from pathlib import Path
import re

from app.services.capability_service import get_capabilities
from app.services.diagnostics_service import write_review_diagnostics
from app.services.preset_service import apply_preset_defaults, get_review_preset
from app.services.runtime import TASK_EXECUTION_LOCK
from app.services.run_store import RunStore
from app.settings import load_settings
from app.workflows.pipeline import BASE_EXPERT_VIEW, run_revision


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w.\-\u4e00-\u9fff]+", "_", Path(name or "").name).strip("._")
    return cleaned or "document.docx"


def _safe_output_name(input_name: str) -> str:
    stem = Path(input_name).stem or "document"
    suffix = Path(input_name).suffix or ".docx"
    return f"{stem}_修订版_{_now_stamp()}{suffix}"


@contextmanager
def _temporary_env(overrides: dict[str, str | None]):
    sentinel = object()
    original: dict[str, object] = {}
    for key, value in overrides.items():
        original[key] = os.environ.get(key, sentinel)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = str(value)
    try:
        yield
    finally:
        for key, value in original.items():
            if value is sentinel:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(value)


class _RunLogWriter(io.TextIOBase):
    def __init__(self, store: RunStore, run_id: str):
        self.store = store
        self.run_id = run_id
        self._buffer = ""

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        if not text:
            return 0
        self._buffer += text.replace("\r\n", "\n")
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._emit(line)
        return len(text)

    def flush(self) -> None:
        if self._buffer:
            self._emit(self._buffer)
            self._buffer = ""

    def _emit(self, text: str) -> None:
        message = (text or "").strip()
        if not message:
            return
        self.store.append_event(self.run_id, event_type="run.log", message=message)


@dataclass
class ReviewRequest:
    filename: str
    file_bytes: bytes
    intent: str = ""
    expert_view: str = BASE_EXPERT_VIEW
    constraints: list[str] = field(default_factory=list)
    preset_key: str = "general_academic"
    revision_engine: str = "auto"
    format_profile: str = "none"
    auto_approve: bool = True
    allow_python_docx_fallback: bool = False
    comment_author: str = "呆塔大师兄"
    strip_existing_comments: bool = False
    prefer_replace: bool = False
    allow_expansion: bool = False
    expansion_level: str = "none"
    allow_web_search: bool = False
    focus_only: bool = False
    memory_scope: str = "document"
    inline_context: str = "boundary"
    chunk_context: int = 2
    context_max_chars: int = 1200
    extract_docx_images: bool = False
    extract_tables: bool = False
    table_image_understanding: bool = False
    table_image_prompt: str = "描述分析这张图"
    parallel_review: bool = True
    parallel_workers: int = 4
    chunk_size: int = 40
    parallel_min_paragraphs: int = 80
    model_override: str = ""
    diagnostics: bool = True
    diagnostics_only: bool = False

    def to_store_params(self) -> dict:
        payload = asdict(self)
        payload.pop("file_bytes", None)
        return payload


def _validate_request(request: ReviewRequest, root_dir: str) -> None:
    allowed_suffixes = {".docx", ".docm", ".dotx", ".dotm"}
    suffix = Path(request.filename).suffix.lower()
    if suffix not in allowed_suffixes:
        raise ValueError("Only .docx/.docm/.dotx/.dotm files are supported")
    if not request.intent.strip() and not request.diagnostics_only:
        raise ValueError("Intent is required")

    capabilities = get_capabilities(root_dir)
    features = capabilities.get("features", {})
    has_win32 = bool(features.get("win32"))
    has_python_docx = bool(features.get("python_docx"))

    if not has_win32 and not has_python_docx:
        raise RuntimeError("No revision engine is available. Install pywin32 or python-docx first.")
    if request.revision_engine == "win32com" and not has_win32:
        raise RuntimeError("Win32 Word engine is unavailable on this machine.")
    if request.revision_engine == "python-docx" and not has_python_docx:
        raise RuntimeError("python-docx engine is unavailable on this machine.")
    if request.revision_engine == "auto" and not has_win32 and not request.allow_python_docx_fallback:
        raise RuntimeError(
            "Auto mode would fail without Win32 Word. Enable python-docx fallback or select python-docx explicitly."
        )
    if request.format_profile != "none" and not has_win32:
        raise RuntimeError("Formatting profiles require Win32 Word.")


def _collect_artifacts(store: RunStore, run_id: str, output_path: Path) -> None:
    artifact_specs = [
        ("revised_docx", "修订文档", output_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("summary_json", "修订摘要(JSON)", output_path.with_suffix(".summary.json"), "application/json"),
        ("log_txt", "运行日志", output_path.with_suffix(".log.txt"), "text/plain"),
        ("diagnostics_json", "学术诊断(JSON)", output_path.with_suffix(".diagnostics.json"), "application/json"),
        ("tables_json", "表格元素(JSON)", output_path.with_suffix(".tables.json"), "application/json"),
        ("images_json", "文档图片(JSON)", output_path.with_suffix(".images.json"), "application/json"),
    ]
    for name, label, path, content_type in artifact_specs:
        if path.exists():
            store.add_artifact(run_id, name=name, label=label, path=path, content_type=content_type)


def _run_dir(store: RunStore, run_id: str) -> Path:
    record = store.get_internal_run(run_id)
    if record is None:
        raise KeyError(run_id)
    return Path(record["run_dir"])


def _execute_review_run(store: RunStore, run_id: str, request: ReviewRequest) -> None:
    run_dir = _run_dir(store, run_id)
    input_filename = _safe_filename(request.filename)
    input_path = run_dir / input_filename
    output_path = run_dir / _safe_output_name(input_filename)
    input_path.write_bytes(request.file_bytes)

    settings = load_settings()
    if request.model_override.strip():
        settings.model = request.model_override.strip()
    settings.revision_engine = request.revision_engine
    settings.auto_approve = bool(request.auto_approve)
    resolved_expert, resolved_format, resolved_constraints = apply_preset_defaults(
        request.preset_key,
        expert_view=request.expert_view,
        format_profile=request.format_profile,
        constraints=request.constraints,
    )
    settings.format_profile = resolved_format

    env_updates = {
        "ALLOW_PYTHON_DOCX_FALLBACK": "true" if request.allow_python_docx_fallback else "false",
        "COMMENT_AUTHOR": request.comment_author,
        "STRIP_EXISTING_COMMENTS": "true" if request.strip_existing_comments else "false",
        "REVIEW_PREFER_REPLACE": "true" if request.prefer_replace else "false",
        "ENABLE_WEB_SEARCH": "true" if request.allow_web_search else "false",
        "REVIEW_ENABLE_FOCUS_FILTER": "true" if request.focus_only else "false",
        "REVIEW_MEMORY_SCOPE": request.memory_scope,
        "REVIEW_INLINE_CONTEXT": request.inline_context,
        "REVIEW_CHUNK_CONTEXT": str(int(request.chunk_context)),
        "REVIEW_CONTEXT_MAX_CHARS": str(int(request.context_max_chars)),
        "EXTRACT_DOCX_IMAGES": "true" if request.extract_docx_images else "false",
        "EXTRACT_TABLE_ELEMENTS": "true" if (request.extract_tables or request.table_image_understanding) else "false",
        "TABLE_IMAGE_UNDERSTANDING": "true" if request.table_image_understanding else "false",
        "TABLE_IMAGE_PROMPT": request.table_image_prompt or "描述分析这张图",
        "REVIEW_PARALLEL": "true" if request.parallel_review else "false",
        "REVIEW_PARALLEL_WORKERS": str(int(request.parallel_workers)),
        "REVIEW_SECTION_CHUNK_SIZE": str(int(request.chunk_size)),
        "REVIEW_PARALLEL_MIN_PARAGRAPHS": str(int(request.parallel_min_paragraphs)),
    }
    logger = _RunLogWriter(store, run_id)

    store.update_status(run_id, status="queued")
    store.append_event(run_id, event_type="run.log", message="Run created and waiting for execution lock")
    store.append_event(
        run_id,
        event_type="run.log",
        message=f"Preset selected: {get_review_preset(request.preset_key).label}",
    )

    with TASK_EXECUTION_LOCK:
        store.update_status(run_id, status="running")
        store.append_event(run_id, event_type="run.log", message="Review workflow started")
        try:
            result = {}
            if not request.diagnostics_only:
                with _temporary_env(env_updates), redirect_stdout(logger), redirect_stderr(logger):
                    result = run_revision(
                        settings=settings,
                        input_path=str(input_path),
                        output_path=str(output_path),
                        intent=request.intent,
                        expert_view=resolved_expert or BASE_EXPERT_VIEW,
                        constraints=resolved_constraints,
                        allow_expansion=bool(request.allow_expansion),
                        expansion_level=request.expansion_level,
                        allow_web_search=bool(request.allow_web_search),
                    )
            if request.diagnostics:
                diagnostics_path = write_review_diagnostics(
                    input_path=str(input_path),
                    output_path=str(output_path),
                    preset_key=request.preset_key,
                )
                store.append_event(run_id, event_type="run.log", message=f"Diagnostics generated: {diagnostics_path.name}")
            else:
                diagnostics_path = output_path.with_suffix(".diagnostics.json")
            logger.flush()
            summary_path = output_path.with_suffix(".summary.json")
            log_path = output_path.with_suffix(".log.txt")
            result_payload = {
                "preset_key": request.preset_key,
                "input_path": str(input_path),
                "output_path": str(output_path),
                "summary_path": str(summary_path) if summary_path.exists() else "",
                "log_path": str(log_path) if log_path.exists() else "",
                "diagnostics_path": str(diagnostics_path) if diagnostics_path.exists() else "",
            }
            if isinstance(result, dict) and result.get("messages"):
                last = result["messages"][-1]
                content = getattr(last, "content", None)
                result_payload["model_output"] = content if content is not None else str(last)
            _collect_artifacts(store, run_id, output_path)
            store.set_result(run_id, result_payload)
            store.update_status(run_id, status="completed")
        except Exception as exc:  # noqa: BLE001
            logger.flush()
            store.set_result(
                run_id,
                {
                    "preset_key": request.preset_key,
                    "input_path": str(input_path),
                    "output_path": str(output_path),
                },
            )
            store.update_status(run_id, status="failed", error=str(exc))


def create_review_run(store: RunStore, request: ReviewRequest, *, root_dir: str) -> dict:
    _validate_request(request, root_dir)
    title = f"{Path(request.filename).name} · {request.intent.strip()[:20]}".strip()
    record = store.create_run(
        mode="review",
        input_filename=request.filename,
        params=request.to_store_params(),
        title=title,
    )
    import threading

    thread = threading.Thread(target=_execute_review_run, args=(store, record["id"], request), daemon=True)
    thread.start()
    return store.get_run(record["id"]) or record
