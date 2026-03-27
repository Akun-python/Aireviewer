from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
import os
from pathlib import Path
import re
import threading

from app.services.runtime import TASK_EXECUTION_LOCK
from app.services.run_store import RunStore
from app.settings import load_settings
from app.tools.path_utils import ensure_parent, resolve_path


DEFAULT_FRAMEWORK = ""


def _load_report_workflows():
    from app.workflows.report import DEFAULT_FRAMEWORK as report_default_framework
    from app.workflows.report import complete_report_docx, generate_report

    return report_default_framework, complete_report_docx, generate_report


def _load_integrate_workflow():
    from app.workflows.report_integrate import integrate_report_chapters

    return integrate_report_chapters


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_name(value: str, *, fallback: str) -> str:
    cleaned = re.sub(r"[^\w.\-\u4e00-\u9fff]+", "_", (value or "").strip()).strip("._")
    return cleaned or fallback


def _safe_topic_name(topic: str, suffix: str) -> str:
    stem = _safe_name(topic, fallback="report")
    return f"{stem}_{suffix}_{_now_stamp()}.docx"


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


class _RunLogger:
    def __init__(self, store: RunStore, run_id: str):
        self.store = store
        self.run_id = run_id

    def __call__(self, message: str) -> None:
        text = (message or "").strip()
        if text:
            self.store.append_event(self.run_id, event_type="run.log", message=text)


@dataclass
class ReportRequest:
    topic: str
    framework_text: str = DEFAULT_FRAMEWORK
    total_chars: int = 10000
    allow_web_search: bool = True
    max_results_per_query: int = 5
    section_timeout: int = 300
    max_section_retries: int = 2
    section_workers: int = 3
    report_docx_engine: str = "auto"
    format_profile: str = "thesis_standard"
    toc_position: str = "before_outline"
    model_override: str = ""

    def to_store_params(self) -> dict:
        return asdict(self)


@dataclass
class ReportCompleteRequest:
    filename: str
    file_bytes: bytes
    topic: str = ""
    allow_web_search: bool = True
    max_results_per_query: int = 5
    section_timeout: int = 300
    fill_empty_headings: bool = True
    format_profile: str = "thesis_standard"
    toc_position: str = "before_outline"
    model_override: str = ""

    def to_store_params(self) -> dict:
        payload = asdict(self)
        payload.pop("file_bytes", None)
        return payload


@dataclass
class ReportIntegrateRequest:
    chapter_files: list[tuple[str, bytes]] = field(default_factory=list)
    topic: str = ""
    toc_position: str = "after_title"
    format_profile: str = "thesis_standard"
    allow_llm: bool = True
    auto_captions: bool = True
    fixed_order: list[str] = field(default_factory=list)
    model_override: str = ""

    def to_store_params(self) -> dict:
        return {
            "chapter_filenames": [name for name, _ in self.chapter_files],
            "topic": self.topic,
            "toc_position": self.toc_position,
            "format_profile": self.format_profile,
            "allow_llm": self.allow_llm,
            "auto_captions": self.auto_captions,
            "fixed_order": list(self.fixed_order),
            "model_override": self.model_override,
        }


def _write_logs(output_path: Path, logs: list[str]) -> Path | None:
    if not logs:
        return None
    log_path = output_path.with_suffix(".log.txt")
    try:
        ensure_parent(log_path)
        log_path.write_text("\n".join(logs), encoding="utf-8")
        return log_path
    except Exception:
        return None


def _collect_report_artifacts(store: RunStore, run_id: str, result: dict) -> None:
    output_path = resolve_path(result.get("output_path", "")) if result.get("output_path") else None
    if output_path and output_path.exists():
        store.add_artifact(
            run_id,
            name="report_docx",
            label="Word 结果文档",
            path=output_path,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    for key, label, content_type in [
        ("text_path", "报告正文(.txt)", "text/plain"),
        ("sources_path", "检索来源(JSON)", "application/json"),
        ("outline_path", "报告大纲(JSON)", "application/json"),
        ("stats_path", "质量统计(JSON)", "application/json"),
        ("analysis_path", "整合分析(JSON)", "application/json"),
    ]:
        raw = result.get(key)
        if not isinstance(raw, str) or not raw:
            continue
        path = resolve_path(raw)
        if path.exists():
            store.add_artifact(run_id, name=key, label=label, path=path, content_type=content_type)
    if output_path:
        log_path = output_path.with_suffix(".log.txt")
        if log_path.exists():
            store.add_artifact(run_id, name="log_txt", label="运行日志", path=log_path, content_type="text/plain")


def _run_dir(store: RunStore, run_id: str) -> Path:
    record = store.get_internal_run(run_id)
    if record is None:
        raise KeyError(run_id)
    return Path(record["run_dir"])


def _build_settings(model_override: str):
    settings = load_settings()
    if model_override.strip():
        settings.model = model_override.strip()
    return settings


def _report_env(*, toc_position: str | None, format_profile: str | None, docx_engine: str | None = None) -> dict[str, str | None]:
    return {
        "REPORT_DOCX_ENGINE": (docx_engine or "").strip() or None,
        "REPORT_TOC_POSITION": (toc_position or "").strip() or None,
        "REPORT_FORMAT_PROFILE": (format_profile or "").strip() or None,
    }


def _execute_report_run(store: RunStore, run_id: str, request: ReportRequest) -> None:
    run_dir = _run_dir(store, run_id)
    output_path = run_dir / _safe_topic_name(request.topic, "课题报告")
    logger = _RunLogger(store, run_id)
    store.update_status(run_id, status="queued")
    with TASK_EXECUTION_LOCK:
        store.update_status(run_id, status="running")
        try:
            settings = _build_settings(request.model_override)
            report_default_framework, _complete_report_docx, generate_report = _load_report_workflows()
            with _temporary_env(
                _report_env(
                    toc_position=request.toc_position,
                    format_profile=request.format_profile,
                    docx_engine=request.report_docx_engine,
                )
            ):
                result = generate_report(
                    settings=settings,
                    topic=request.topic,
                    output_path=str(output_path),
                    framework_text=request.framework_text or report_default_framework,
                    total_chars=int(request.total_chars),
                    allow_web_search=bool(request.allow_web_search),
                    max_results_per_query=int(request.max_results_per_query),
                    section_timeout=int(request.section_timeout),
                    max_section_retries=int(request.max_section_retries),
                    section_workers=int(request.section_workers),
                    format_profile=request.format_profile,
                    logger=logger,
                )
            _write_logs(output_path, result.get("logs", []) if isinstance(result.get("logs"), list) else [])
            _collect_report_artifacts(store, run_id, result)
            store.set_result(run_id, result)
            store.update_status(run_id, status="completed")
        except Exception as exc:  # noqa: BLE001
            store.set_result(run_id, {"output_path": str(output_path)})
            store.update_status(run_id, status="failed", error=str(exc))


def _execute_report_complete_run(store: RunStore, run_id: str, request: ReportCompleteRequest) -> None:
    run_dir = _run_dir(store, run_id)
    input_name = _safe_name(request.filename, fallback="report.docx")
    input_path = run_dir / input_name
    output_path = run_dir / _safe_topic_name(Path(input_name).stem or "report", "完善")
    input_path.write_bytes(request.file_bytes)
    logger = _RunLogger(store, run_id)
    store.update_status(run_id, status="queued")
    with TASK_EXECUTION_LOCK:
        store.update_status(run_id, status="running")
        try:
            settings = _build_settings(request.model_override)
            _report_default_framework, complete_report_docx, _generate_report = _load_report_workflows()
            with _temporary_env(_report_env(toc_position=request.toc_position, format_profile=request.format_profile)):
                result = complete_report_docx(
                    settings=settings,
                    input_path=str(input_path),
                    output_path=str(output_path),
                    topic=request.topic.strip(),
                    allow_web_search=bool(request.allow_web_search),
                    max_results_per_query=int(request.max_results_per_query),
                    section_timeout=int(request.section_timeout),
                    fill_empty_headings=bool(request.fill_empty_headings),
                    format_profile=request.format_profile,
                    logger=logger,
                )
            _write_logs(output_path, result.get("logs", []) if isinstance(result.get("logs"), list) else [])
            _collect_report_artifacts(store, run_id, result)
            store.set_result(run_id, result)
            store.update_status(run_id, status="completed")
        except Exception as exc:  # noqa: BLE001
            store.set_result(run_id, {"input_path": str(input_path), "output_path": str(output_path)})
            store.update_status(run_id, status="failed", error=str(exc))


def _execute_report_integrate_run(store: RunStore, run_id: str, request: ReportIntegrateRequest) -> None:
    run_dir = _run_dir(store, run_id)
    chapters_dir = run_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    chapter_paths: list[str] = []
    for index, (filename, data) in enumerate(request.chapter_files, start=1):
        safe_name = _safe_name(filename, fallback=f"chapter_{index}.docx")
        chapter_path = chapters_dir / safe_name
        chapter_path.write_bytes(data)
        chapter_paths.append(str(chapter_path))
    output_path = run_dir / _safe_topic_name(request.topic or "整合报告", "整合")
    logger = _RunLogger(store, run_id)
    store.update_status(run_id, status="queued")
    with TASK_EXECUTION_LOCK:
        store.update_status(run_id, status="running")
        try:
            settings = _build_settings(request.model_override)
            integrate_report_chapters = _load_integrate_workflow()
            with _temporary_env(_report_env(toc_position=request.toc_position, format_profile=request.format_profile)):
                result = integrate_report_chapters(
                    settings=settings,
                    chapter_paths=chapter_paths,
                    output_path=str(output_path),
                    topic=request.topic.strip(),
                    toc_position=request.toc_position,
                    format_profile=request.format_profile,
                    allow_llm=bool(request.allow_llm),
                    auto_captions=bool(request.auto_captions),
                    fixed_order=request.fixed_order or None,
                    logger=logger,
                )
            _collect_report_artifacts(store, run_id, result)
            store.set_result(run_id, result)
            store.update_status(run_id, status="completed")
        except Exception as exc:  # noqa: BLE001
            store.set_result(run_id, {"output_path": str(output_path)})
            store.update_status(run_id, status="failed", error=str(exc))


def create_report_run(store: RunStore, request: ReportRequest) -> dict:
    record = store.create_run(
        mode="report",
        input_filename=request.topic,
        params=request.to_store_params(),
        title=f"{request.topic} · 课题报告",
    )
    threading.Thread(target=_execute_report_run, args=(store, record["id"], request), daemon=True).start()
    return store.get_run(record["id"]) or record


def create_report_complete_run(store: RunStore, request: ReportCompleteRequest) -> dict:
    record = store.create_run(
        mode="report-complete",
        input_filename=request.filename,
        params=request.to_store_params(),
        title=f"{request.filename} · 报告完善",
    )
    threading.Thread(target=_execute_report_complete_run, args=(store, record["id"], request), daemon=True).start()
    return store.get_run(record["id"]) or record


def create_report_integrate_run(store: RunStore, request: ReportIntegrateRequest) -> dict:
    title = f"{request.topic or '整合报告'} · 多章整合"
    record = store.create_run(
        mode="report-integrate",
        input_filename=request.topic or "chapters",
        params=request.to_store_params(),
        title=title,
    )
    threading.Thread(target=_execute_report_integrate_run, args=(store, record["id"], request), daemon=True).start()
    return store.get_run(record["id"]) or record
