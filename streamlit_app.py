from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
import re

import streamlit as st

from app.services.diagnostics_service import write_review_diagnostics
from app.services.preset_service import apply_preset_defaults, list_review_presets
from app.settings import AppSettings, load_settings
from app.workflows.pipeline import BASE_CONSTRAINTS, BASE_EXPERT_VIEW, SUMMARY_TEMPLATE, run_revision
from app.workflows.report import DEFAULT_FRAMEWORK, generate_report, complete_report_docx
from app.workflows.report_integrate import integrate_report_chapters
from app.tools.path_utils import resolve_path


_CHAT_STATE_INIT_KEY = "reviewer_chat_initialized"
_CHAT_SESSIONS_KEY = "reviewer_chat_sessions"
_CHAT_ACTIVE_SESSION_KEY = "reviewer_chat_active_session_id"
_CHAT_HISTORY_PATH_KEY = "reviewer_chat_history_path"
_CHAT_SESSION_SELECT_KEY = "reviewer_chat_session_select"
_CHAT_SESSION_TITLE_INPUT_PREFIX = "reviewer_chat_session_title_input"
_CHAT_PENDING_WIDGET_STATE_KEY = "reviewer_chat_pending_widget_state"
_INTENT_INPUT_KEY = "reviewer_intent_input"
_INTENT_PROMPT_SELECT_KEY = "reviewer_intent_prompt_select"
_REVIEW_PRESET_KEY = "reviewer_review_preset_key"
_REVIEW_DIAGNOSTICS_KEY = "reviewer_review_diagnostics"
_REVIEW_DIAGNOSTICS_ONLY_KEY = "reviewer_review_diagnostics_only"
_FOCUS_FILTER_KEY = "reviewer_focus_filter_only_targets"
_FORMAT_PROFILE_SELECT_KEY = "reviewer_format_profile_select"
_MEMORY_SCOPE_KEY = "reviewer_review_memory_scope"
_INLINE_CONTEXT_KEY = "reviewer_review_inline_context"
_CHUNK_CONTEXT_KEY = "reviewer_review_chunk_context"
_CTX_MAX_CHARS_KEY = "reviewer_review_context_max_chars"
_TABLE_EXTRACT_KEY = "reviewer_extract_table_elements"
_TABLE_IMAGE_UNDERSTANDING_KEY = "reviewer_table_image_understanding"
_TABLE_IMAGE_PROMPT_KEY = "reviewer_table_image_prompt"
_DOCX_IMAGE_EXTRACT_KEY = "reviewer_extract_docx_images"
_REPORT_TOPIC_KEY = "reviewer_report_topic"
_REPORT_FRAMEWORK_KEY = "reviewer_report_framework"
_REPORT_LAST_RESULT_KEY = "reviewer_report_last_result"
_REPORT_COMPLETE_TOPIC_KEY = "reviewer_report_complete_topic"
_REPORT_COMPLETE_LAST_RESULT_KEY = "reviewer_report_complete_last_result"
_REPORT_COMPLETE_UPLOAD_KEY = "reviewer_report_complete_upload"
_REPORT_INTEGRATE_LAST_RESULT_KEY = "reviewer_report_integrate_last_result"
_REPORT_INTEGRATE_UPLOAD_KEY = "reviewer_report_integrate_uploads"
_MODE_KEY = "reviewer_app_mode"


def _prepare_workspace(root_dir: str) -> Path:
    workspace = Path(root_dir) / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def _chat_history_path(workspace: Path) -> Path:
    return workspace / "reviewer_chat_sessions.json"


def _now_iso() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat(sep=" ")


def _rerun() -> None:
    rerun_fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if callable(rerun_fn):
        rerun_fn()


def _queue_widget_state(widget_key: str, value) -> None:
    pending = st.session_state.get(_CHAT_PENDING_WIDGET_STATE_KEY)
    if not isinstance(pending, dict):
        pending = {}
        st.session_state[_CHAT_PENDING_WIDGET_STATE_KEY] = pending
    pending[widget_key] = value


def _apply_queued_widget_state() -> None:
    pending = st.session_state.get(_CHAT_PENDING_WIDGET_STATE_KEY)
    if not isinstance(pending, dict) or not pending:
        return
    for widget_key, value in list(pending.items()):
        if isinstance(widget_key, str) and widget_key:
            st.session_state[widget_key] = value
    st.session_state[_CHAT_PENDING_WIDGET_STATE_KEY] = {}


def _safe_read_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except Exception:
        return None


def _safe_read_text(path: Path, *, encoding: str = "utf-8") -> str | None:
    try:
        return path.read_text(encoding=encoding)
    except Exception:
        return None


def _try_load_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None


def _env_int(name: str, default: int, *, min_value: int = 1) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return max(min_value, int(default))
    try:
        value = int(raw)
    except Exception:
        value = int(default)
    return max(min_value, value)


def _streamlit_log_tail_lines() -> int:
    return _env_int("STREAMLIT_LOG_TAIL_LINES", 300, min_value=20)


def _streamlit_log_buffer_lines() -> int:
    return _env_int("STREAMLIT_LOG_BUFFER_LINES", 3000, min_value=200)


def _streamlit_log_update_interval_seconds() -> float:
    interval_ms = _env_int("STREAMLIT_LOG_UPDATE_INTERVAL_MS", 400, min_value=0)
    return max(0.0, float(interval_ms) / 1000.0)


def _tail_lines_text(text: str, max_lines: int) -> str:
    if max_lines <= 0:
        return text
    lines = (text or "").splitlines()
    if len(lines) <= max_lines:
        return text
    omitted = len(lines) - max_lines
    tail = "\n".join(lines[-max_lines:])
    return f"...（仅显示最后{max_lines}行，已省略{omitted}行）\n{tail}"


def _build_throttled_log_writer(log_box, log_lines: list[str]):
    interval_s = _streamlit_log_update_interval_seconds()
    tail_lines = _streamlit_log_tail_lines()
    buffer_lines = _streamlit_log_buffer_lines()
    disabled = False
    last_render_ts = 0.0

    def _render(*, force: bool) -> None:
        nonlocal disabled, last_render_ts
        if disabled:
            return
        now = time.monotonic()
        if not force and interval_s > 0 and (now - last_render_ts) < interval_s:
            return
        last_render_ts = now
        try:
            content = "\n".join(log_lines[-tail_lines:]) if tail_lines > 0 else "\n".join(log_lines)
            log_box.code(content)
        except Exception:
            # Browser websocket may already be closed; stop UI writes silently.
            disabled = True

    def _logger(message: str) -> None:
        log_lines.append(message)
        if len(log_lines) > buffer_lines:
            del log_lines[:-buffer_lines]
        _render(force=False)

    def _flush() -> None:
        _render(force=True)

    return _logger, _flush


def _resolve_prompt_dir(root_dir: str) -> Path | None:
    for name in ("prompt", "promt"):
        candidate = Path(root_dir) / name
        if candidate.is_dir():
            return candidate
    return None


def _list_prompt_files(prompt_dir: Path) -> list[Path]:
    try:
        return sorted([p for p in prompt_dir.glob("*.txt") if p.is_file()], key=lambda p: p.name)
    except Exception:
        return []


def _open_in_file_manager(path: Path) -> tuple[bool, str]:
    try:
        target = str(path)
        if os.name == "nt":
            os.startfile(target)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target], close_fds=True)
        else:
            subprocess.Popen(["xdg-open", target], close_fds=True)
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _load_chat_history(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "active_session_id": None, "sessions": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"version": 1, "active_session_id": None, "sessions": []}
    if not isinstance(payload, dict):
        return {"version": 1, "active_session_id": None, "sessions": []}
    sessions = payload.get("sessions", [])
    if not isinstance(sessions, list):
        sessions = []
    active_session_id = payload.get("active_session_id")
    if active_session_id is not None and not isinstance(active_session_id, str):
        active_session_id = None
    return {"version": 1, "active_session_id": active_session_id, "sessions": sessions}


def _save_chat_history(path: Path, sessions: list[dict], active_session_id: str | None) -> None:
    payload = {"version": 1, "active_session_id": active_session_id, "sessions": sessions}
    try:
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(path)
    except Exception:
        return


def _new_chat_session(title: str | None = None) -> dict:
    now = _now_iso()
    return {
        "id": uuid.uuid4().hex,
        "title": title or f"会话 {now}",
        "created_at": now,
        "updated_at": now,
        "runs": [],
    }


def _init_chat_state(workspace: Path, persist_sessions: bool) -> None:
    if st.session_state.get(_CHAT_STATE_INIT_KEY):
        return

    history_path = _chat_history_path(workspace)
    sessions: list[dict] = []
    active_session_id: str | None = None
    if persist_sessions:
        payload = _load_chat_history(history_path)
        sessions = payload.get("sessions", []) if isinstance(payload.get("sessions"), list) else []
        active_session_id = payload.get("active_session_id")

    now = _now_iso()
    normalized_sessions: list[dict] = []
    for session in sessions:
        if not isinstance(session, dict):
            continue
        session_id = session.get("id")
        if not isinstance(session_id, str) or not session_id:
            continue
        created_at = session.get("created_at") if isinstance(session.get("created_at"), str) else ""
        updated_at = session.get("updated_at") if isinstance(session.get("updated_at"), str) else ""
        title = session.get("title") if isinstance(session.get("title"), str) else ""
        if not created_at:
            created_at = now
        if not updated_at:
            updated_at = created_at
        if not title:
            title = f"会话 {created_at}"
        session["created_at"] = created_at
        session["updated_at"] = updated_at
        session["title"] = title
        if not isinstance(session.get("runs"), list):
            session["runs"] = []
        normalized_sessions.append(session)
    sessions = normalized_sessions

    if not sessions:
        session = _new_chat_session()
        sessions = [session]
        active_session_id = session["id"]
        if persist_sessions:
            _save_chat_history(history_path, sessions, active_session_id)

    valid_ids = [s.get("id") for s in sessions if isinstance(s, dict) and isinstance(s.get("id"), str)]
    if active_session_id not in valid_ids:
        active_session_id = valid_ids[0] if valid_ids else None

    st.session_state[_CHAT_HISTORY_PATH_KEY] = str(history_path)
    st.session_state[_CHAT_SESSIONS_KEY] = sessions
    st.session_state[_CHAT_ACTIVE_SESSION_KEY] = active_session_id
    st.session_state[_CHAT_SESSION_SELECT_KEY] = active_session_id
    st.session_state[_CHAT_STATE_INIT_KEY] = True


def _persist_chat_state(persist_sessions: bool) -> None:
    if not persist_sessions:
        return
    path_raw = st.session_state.get(_CHAT_HISTORY_PATH_KEY)
    if not isinstance(path_raw, str) or not path_raw:
        return
    sessions = st.session_state.get(_CHAT_SESSIONS_KEY)
    if not isinstance(sessions, list):
        return
    sessions = [session for session in sessions if isinstance(session, dict)]
    active_session_id = st.session_state.get(_CHAT_ACTIVE_SESSION_KEY)
    if active_session_id is not None and not isinstance(active_session_id, str):
        active_session_id = None
    _save_chat_history(Path(path_raw), sessions, active_session_id)


def _get_active_session() -> dict | None:
    sessions = st.session_state.get(_CHAT_SESSIONS_KEY)
    if not isinstance(sessions, list):
        return None
    active_session_id = st.session_state.get(_CHAT_ACTIVE_SESSION_KEY)
    if not isinstance(active_session_id, str) or not active_session_id:
        return None
    for session in sessions:
        if isinstance(session, dict) and session.get("id") == active_session_id:
            return session
    return None


def _render_chat_message(role: str, render_fn) -> None:
    chat_message = getattr(st, "chat_message", None)
    if callable(chat_message):
        with chat_message(role):
            render_fn()
        return
    label = "用户" if role == "user" else "助手"
    with st.container():
        st.markdown(f"**{label}**")
        render_fn()


def _save_upload(uploaded_file, workspace: Path) -> Path:
    filename = Path(uploaded_file.name).name
    suffix = Path(filename).suffix or ".docx"
    tmp_dir = Path(tempfile.mkdtemp(prefix="run_", dir=str(workspace)))
    input_path = tmp_dir / f"input{suffix}"
    input_path.write_bytes(uploaded_file.getvalue())
    return input_path


def _build_output_path(uploaded_name: str, workspace: Path) -> Path:
    safe_name = Path(uploaded_name).name
    stem = Path(safe_name).stem or "document"
    suffix = Path(safe_name).suffix or ".docx"
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{stem}_修订版_{timestamp}{suffix}"
    return workspace / filename


def _parse_extra_constraints(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _has_win32() -> bool:
    if os.name != "nt":
        return False
    try:
        import pythoncom  # type: ignore  # noqa: F401
        import win32com  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def _has_python_docx() -> bool:
    try:
        import docx  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def _has_langgraph_sqlite() -> bool:
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def _has_tavily_key() -> bool:
    return bool(os.getenv("TAVILY_API_KEY", "").strip())


def _has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip() or os.getenv("API_KEY", "").strip())


def _has_apiyi_key() -> bool:
    return bool(os.getenv("APIYI_API_KEY", "").strip())


def _safe_report_filename(topic: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", topic or "").strip("_")
    if not cleaned:
        cleaned = "topic"
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{cleaned}_课题报告_{timestamp}.docx"


def _safe_report_completion_filename(name: str) -> str:
    stem = Path(name or "").stem or "report"
    cleaned = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", stem).strip("_")
    if not cleaned:
        cleaned = "report"
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{cleaned}_完善_{timestamp}.docx"


def _safe_report_integration_filename(topic: str, *, chapter_count: int) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", topic or "").strip("_")
    if not cleaned:
        cleaned = "report"
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{cleaned}_整合_{chapter_count}章_{timestamp}.docx"


def _render_report_ui(settings: AppSettings, workspace: Path) -> None:
    st.header("课题报告生成")
    st.caption("输入选题与框架，系统将联网检索并生成万字左右课题报告（优先使用 Win32 Word 引擎）。")

    model_override = st.sidebar.text_input("模型覆盖(可选)", value="", key="report_model_override")
    if model_override:
        settings.model = model_override
    if (settings.model or "").strip().lower().startswith("openai:") and not _has_openai_key():
        st.sidebar.error("未检测到 OPENAI_API_KEY/API_KEY，模型调用将失败；请先配置环境变量或 .env。")

    topic = st.text_input("选题/题目", key=_REPORT_TOPIC_KEY)
    framework_text = st.text_area(
        "报告框架(可编辑)",
        value=st.session_state.get(_REPORT_FRAMEWORK_KEY, DEFAULT_FRAMEWORK),
        height=220,
        key=_REPORT_FRAMEWORK_KEY,
    )
    total_chars = st.slider("目标字数(约)", min_value=6000, max_value=15000, value=10000, step=500)
    report_docx_engine = st.selectbox(
        "Word生成引擎",
        options=["auto", "win32com", "python-docx"],
        index=0,
        format_func=lambda x: {"auto": "自动(推荐)", "win32com": "Win32 Word", "python-docx": "python-docx"}.get(x, x),
        help="auto 会在可用时优先使用 Win32 Word；python-docx 会生成较朴素的 docx（不含 Word 原生目录/多级编号）。",
        key="report_docx_engine",
    )
    try:
        from app.formatting.profiles import PROFILES  # noqa: WPS433

        report_format_all = [p.key for p in PROFILES]
    except Exception:
        report_format_all = ["none", "thesis_standard", "a4_strict", "zhengda_cup"]
    report_format_options = [key for key in report_format_all if key != "zhengda_cup"]
    if "none" not in report_format_options:
        report_format_options.insert(0, "none")
    default_report_format = "thesis_standard" if "thesis_standard" in report_format_options else "none"
    report_format = st.selectbox(
        "报告排版风格",
        options=report_format_options,
        index=report_format_options.index(default_report_format),
        format_func=lambda x: {"none": "无", "thesis_standard": "论文标准格式", "a4_strict": "A4规范格式"}.get(x, x),
        help="生成后使用 Win32 Word 统一字体/行距/多级编号/目录。",
        key="report_format_profile",
    )
    toc_position = st.selectbox(
        "目录位置",
        options=["before_outline", "after_title", "none"],
        index=0,
        format_func=lambda x: {
            "before_outline": "报告大纲表前",
            "after_title": "标题后",
            "none": "不生成目录",
        }.get(x, x),
        help="控制 Word 目录插入位置（仅论文标准格式生效）。",
        key="report_toc_position",
    )
    max_results = st.slider("每条检索返回数", min_value=3, max_value=8, value=5)
    section_timeout = st.slider(
        "单章节超时(秒)",
        min_value=60,
        max_value=900,
        value=300,
        step=30,
        help="当前用于日志提示（不会强制中断模型调用）；建议结合“章节并行数/重试次数”控制总耗时。",
    )
    max_retries = st.slider("章节重试次数", min_value=0, max_value=3, value=2, step=1)
    section_workers = st.slider("章节并行数", min_value=1, max_value=6, value=3, step=1)
    allow_web_search = st.checkbox("启用联网检索(Tavily)", value=True)

    if allow_web_search and not _has_tavily_key():
        st.warning("未检测到 TAVILY_API_KEY，无法联网检索。请先配置环境变量。")
    if not _has_win32():
        st.warning("未检测到 Win32 Word（pywin32），将回退使用 python-docx 生成报告。")
    if report_docx_engine == "win32com" and not _has_win32():
        st.warning("你选择了 Win32 Word 引擎，但当前未检测到 pywin32，将无法按该引擎生成。")
    if report_format != "none" and not _has_win32():
        st.warning("当前未检测到 Win32 Word（pywin32），无法应用报告排版风格。")

    run_button = st.button("生成课题报告", type="primary")
    status = st.empty()
    log_box = st.empty()

    if run_button:
        if not topic:
            status.error("请输入选题/题目。")
            return
        if allow_web_search and not _has_tavily_key():
            status.error("未配置 TAVILY_API_KEY，无法联网检索。")
            return
        if report_docx_engine == "win32com" and not _has_win32():
            status.error("已选择 Win32 Word 引擎，但未检测到 pywin32。请安装 pywin32 或改为 auto/python-docx。")
            return

        output_name = _safe_report_filename(topic)
        output_path = workspace / "reports" / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)

        status.info("正在生成课题报告，请稍候...")
        log_lines: list[str] = []
        logger_writer, flush_logger = _build_throttled_log_writer(log_box, log_lines)

        try:
            os.environ["REPORT_TOC_POSITION"] = toc_position
            os.environ["REPORT_DOCX_ENGINE"] = report_docx_engine
            result = generate_report(
                settings=settings,
                topic=topic,
                output_path=str(output_path),
                framework_text=framework_text,
                total_chars=total_chars,
                allow_web_search=allow_web_search,
                max_results_per_query=max_results,
                section_timeout=section_timeout,
                max_section_retries=max_retries,
                section_workers=section_workers,
                format_profile=report_format,
                logger=logger_writer,
            )
        except Exception as exc:  # noqa: BLE001
            status.error(f"生成失败：{exc}")
            return
        finally:
            flush_logger()
        status.success("课题报告生成完成。")
        st.session_state[_REPORT_LAST_RESULT_KEY] = result

    latest = st.session_state.get(_REPORT_LAST_RESULT_KEY)
    if isinstance(latest, dict):
        output_path = resolve_path(latest.get("output_path", "")) if latest.get("output_path") else None
        text_path = resolve_path(latest.get("text_path", "")) if latest.get("text_path") else None
        sources_path = resolve_path(latest.get("sources_path", "")) if latest.get("sources_path") else None
        outline_path = resolve_path(latest.get("outline_path", "")) if latest.get("outline_path") else None
        stats_path = resolve_path(latest.get("stats_path", "")) if latest.get("stats_path") else None
        if output_path and output_path.exists():
            try:
                doc_bytes = output_path.read_bytes()
                doc_key = f"report_dl_doc_{output_path.name}_{output_path.stat().st_mtime_ns}"
            except Exception:
                doc_bytes = None
                doc_key = "report_dl_doc_missing"
            st.download_button(
                "下载课题报告(.docx)",
                data=doc_bytes or b"",
                file_name=output_path.name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                key=doc_key,
            )
        if text_path and text_path.exists():
            try:
                text_data = text_path.read_text(encoding="utf-8")
                text_key = f"report_dl_txt_{text_path.name}_{text_path.stat().st_mtime_ns}"
            except Exception:
                text_data = ""
                text_key = "report_dl_txt_missing"
            st.download_button(
                "下载课题报告(.txt)",
                data=text_data,
                file_name=text_path.name,
                mime="text/plain",
                use_container_width=True,
                key=text_key,
            )
        if sources_path and sources_path.exists():
            with st.expander("检索来源(JSON)", expanded=False):
                st.json(json.loads(sources_path.read_text(encoding="utf-8")))
        if stats_path and stats_path.exists():
            try:
                stats_data = stats_path.read_text(encoding="utf-8")
                stats_key = f"report_dl_stats_{stats_path.name}_{stats_path.stat().st_mtime_ns}"
            except Exception:
                stats_data = ""
                stats_key = "report_dl_stats_missing"
            st.download_button(
                "下载质量统计(.json)",
                data=stats_data,
                file_name=stats_path.name,
                mime="application/json",
                use_container_width=True,
                key=stats_key,
            )
            with st.expander("生成质量统计(JSON)", expanded=False):
                st.json(json.loads(stats_path.read_text(encoding="utf-8")))
        stats = latest.get("stats") if isinstance(latest.get("stats"), dict) else None
        if isinstance(stats, dict):
            with st.expander("质量概览", expanded=False):
                st.write(f"- 覆盖率：{stats.get('leaf_coverage')}")
                st.write(f"- 缺失叶子节点：{stats.get('leaf_missing')}")
                st.write(f"- 偏短叶子节点：{stats.get('leaf_short')}")
        if outline_path and outline_path.exists():
            with st.expander("报告大纲(JSON)", expanded=False):
                st.json(json.loads(outline_path.read_text(encoding="utf-8")))
        logs = latest.get("logs")
        if isinstance(logs, list) and logs:
            with st.expander("生成日志", expanded=False):
                st.code(_tail_lines_text("\n".join(logs), _streamlit_log_tail_lines()))

    st.divider()
    with st.expander("完善已有报告（按 Word 目录补全）", expanded=False):
        if not _has_win32():
            st.warning("未检测到 Win32 Word（pywin32），无法使用 Word COM 补全报告。")
        uploaded_report = st.file_uploader(
            "上传待完善的课题报告(.docx)",
            type=["docx"],
            key=_REPORT_COMPLETE_UPLOAD_KEY,
        )
        complete_topic = st.text_input("选题/题目(可选，留空将自动识别)", key=_REPORT_COMPLETE_TOPIC_KEY)
        fill_empty_headings = st.checkbox("补全空标题（无正文）", value=True, key="report_complete_fill_empty")
        complete_button = st.button("补全报告", type="primary", key="report_complete_button")
        status_complete = st.empty()
        log_box_complete = st.empty()

        if complete_button:
            if not uploaded_report:
                status_complete.error("请上传待完善的报告文件。")
                return
            if not _has_win32():
                status_complete.error("未检测到 Win32 Word（pywin32），无法执行补全。")
                return
            allow_web_search_complete = allow_web_search and _has_tavily_key()
            if allow_web_search and not _has_tavily_key():
                status_complete.warning("未检测到 TAVILY_API_KEY，补全将不使用联网检索。")
            input_path = _save_upload(uploaded_report, workspace)
            output_name = _safe_report_completion_filename(uploaded_report.name)
            output_path = workspace / "reports" / output_name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            status_complete.info("正在补全报告，请稍候...")
            log_lines: list[str] = []
            logger_writer, flush_logger = _build_throttled_log_writer(log_box_complete, log_lines)

            try:
                os.environ["REPORT_TOC_POSITION"] = toc_position
                result = complete_report_docx(
                    settings=settings,
                    input_path=str(input_path),
                    output_path=str(output_path),
                    topic=complete_topic.strip() if isinstance(complete_topic, str) else "",
                    allow_web_search=allow_web_search_complete,
                    max_results_per_query=max_results,
                    section_timeout=section_timeout,
                    fill_empty_headings=bool(fill_empty_headings),
                    format_profile=report_format,
                    logger=logger_writer,
                )
            except Exception as exc:  # noqa: BLE001
                status_complete.error(f"补全失败：{exc}")
                return
            finally:
                flush_logger()
            status_complete.success("报告补全完成。")
            st.session_state[_REPORT_COMPLETE_LAST_RESULT_KEY] = result

        latest_complete = st.session_state.get(_REPORT_COMPLETE_LAST_RESULT_KEY)
        if isinstance(latest_complete, dict):
            output_path = resolve_path(latest_complete.get("output_path", "")) if latest_complete.get("output_path") else None
            if output_path and output_path.exists():
                try:
                    doc_bytes = output_path.read_bytes()
                    doc_key = f"report_complete_dl_{output_path.name}_{output_path.stat().st_mtime_ns}"
                except Exception:
                    doc_bytes = None
                    doc_key = "report_complete_dl_missing"
                st.download_button(
                    "下载补全后的报告(.docx)",
                    data=doc_bytes or b"",
                    file_name=output_path.name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key=doc_key,
                )
            logs = latest_complete.get("logs")
            if isinstance(logs, list) and logs:
                with st.expander("补全日志", expanded=False):
                    st.code(_tail_lines_text("\n".join(logs), _streamlit_log_tail_lines()))

    with st.expander("报告整合（多章节 Word 合并）", expanded=False):
        st.caption("上传各章节 Word（已生成的分章文件），系统将读取摘要、生成引言与过渡段，并整合为一份完整报告。")
        uploaded_chapters = st.file_uploader(
            "上传章节Word（.docx，可多选）",
            type=["docx"],
            accept_multiple_files=True,
            key=_REPORT_INTEGRATE_UPLOAD_KEY,
        )
        integrate_topic = st.text_input("整合报告题目(可选)", value="", key="report_integrate_topic")
        order_mode = st.selectbox(
            "章节排序",
            options=["filename", "upload", "manual"],
            index=0,
            format_func=lambda x: {"filename": "按文件名排序(推荐)", "upload": "按上传顺序", "manual": "手动指定顺序"}.get(x, x),
            key="report_integrate_order_mode",
        )
        manual_order_text = ""
        if order_mode == "manual":
            manual_order_text = st.text_area(
                "手动章节顺序（每行一个：可写“章节标题”或“文件名/文件名(不含扩展名)”）",
                value="",
                height=120,
                key="report_integrate_manual_order",
                help="示例：\n引言\n现状分析\n影响因素分析\n对策建议\n结论",
            )
        allow_llm_integrate = st.checkbox("使用模型生成引言/过渡/摘要", value=True, key="report_integrate_allow_llm")
        auto_captions = st.checkbox("自动图表题注编号（图/表）", value=True, key="report_integrate_auto_captions")
        integrate_button = st.button("开始整合生成报告", type="primary", key="report_integrate_button")
        integrate_status = st.empty()
        integrate_log_box = st.empty()

        if integrate_button:
            if not uploaded_chapters:
                integrate_status.error("请先上传至少一个章节 Word 文件。")
                return
            if not _has_win32():
                integrate_status.error("未检测到 Win32 Word（pywin32），无法执行章节整合。")
                return

            tmp_dir = Path(tempfile.mkdtemp(prefix="integrate_", dir=str(workspace)))
            saved_paths: list[Path] = []
            for f in uploaded_chapters:
                name = Path(f.name).name
                target = tmp_dir / name
                try:
                    target.write_bytes(f.getvalue())
                except Exception:
                    continue
                saved_paths.append(target)

            if not saved_paths:
                integrate_status.error("保存上传文件失败，请重试。")
                return

            if order_mode == "filename":
                saved_paths = sorted(saved_paths, key=lambda p: p.name)

            final_topic = integrate_topic.strip() if isinstance(integrate_topic, str) else ""
            if not final_topic:
                final_topic = saved_paths[0].stem

            output_name = _safe_report_integration_filename(final_topic, chapter_count=len(saved_paths))
            output_path = workspace / "reports" / output_name
            output_path.parent.mkdir(parents=True, exist_ok=True)

            integrate_status.info("正在整合报告，请稍候...")
            log_lines: list[str] = []
            logger_writer, flush_logger = _build_throttled_log_writer(integrate_log_box, log_lines)

            fixed_order = None
            if order_mode == "manual" and isinstance(manual_order_text, str) and manual_order_text.strip():
                fixed_order = [line.strip() for line in manual_order_text.splitlines() if line.strip()]

            try:
                os.environ["REPORT_TOC_POSITION"] = toc_position
                result = integrate_report_chapters(
                    settings=settings,
                    chapter_paths=[str(p) for p in saved_paths],
                    output_path=str(output_path),
                    topic=final_topic,
                    toc_position=toc_position,
                    format_profile=report_format,
                    allow_llm=bool(allow_llm_integrate),
                    auto_captions=bool(auto_captions),
                    fixed_order=fixed_order,
                    logger=logger_writer,
                )
            except Exception as exc:  # noqa: BLE001
                integrate_status.error(f"整合失败：{exc}")
                msg = str(exc)
                if "win32com.gen_py" in msg or "CLSIDToPackageMap" in msg or "CLSIDToClassMap" in msg:
                    st.warning(
                        "检测到 pywin32 的 gen_py 缓存损坏。建议：关闭所有 Word 窗口后重试；"
                        "必要时手动清理 win32com 缓存（gen_py）并重启 Streamlit。"
                    )
                return
            finally:
                flush_logger()

            integrate_status.success("报告整合完成。")
            st.session_state[_REPORT_INTEGRATE_LAST_RESULT_KEY] = result

        latest_integrate = st.session_state.get(_REPORT_INTEGRATE_LAST_RESULT_KEY)
        if isinstance(latest_integrate, dict):
            output_path = resolve_path(latest_integrate.get("output_path", "")) if latest_integrate.get("output_path") else None
            analysis_path = (
                resolve_path(latest_integrate.get("analysis_path", ""))
                if latest_integrate.get("analysis_path")
                else None
            )
            if output_path and output_path.exists():
                try:
                    doc_bytes = output_path.read_bytes()
                    doc_key = f"report_integrate_dl_{output_path.name}_{output_path.stat().st_mtime_ns}"
                except Exception:
                    doc_bytes = None
                    doc_key = "report_integrate_dl_missing"
                st.download_button(
                    "下载整合后的报告(.docx)",
                    data=doc_bytes or b"",
                    file_name=output_path.name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key=doc_key,
                )
            if analysis_path and analysis_path.exists():
                try:
                    analysis_bytes = analysis_path.read_bytes()
                    analysis_key = f"report_integrate_json_{analysis_path.name}_{analysis_path.stat().st_mtime_ns}"
                except Exception:
                    analysis_bytes = None
                    analysis_key = "report_integrate_json_missing"
                st.download_button(
                    "下载整合分析(JSON)",
                    data=analysis_bytes or b"",
                    file_name=analysis_path.name,
                    mime="application/json",
                    use_container_width=True,
                    key=analysis_key,
                )
            logs = latest_integrate.get("logs")
            if isinstance(logs, list) and logs:
                with st.expander("整合日志", expanded=False):
                    st.code(_tail_lines_text("\n".join(logs), _streamlit_log_tail_lines()))
def _render_diagnostics_result(diagnostics_path: Path, *, run_id: str, key_prefix: str) -> None:
    diagnostics_text = _safe_read_text(diagnostics_path, encoding="utf-8")
    if diagnostics_text is None:
        st.error(f"读取学术诊断失败：{diagnostics_path}")
        return
    st.download_button(
        "下载学术诊断(JSON)",
        data=diagnostics_text,
        file_name=diagnostics_path.name,
        mime="application/json",
        key=f"{key_prefix}dl_diagnostics_{run_id}",
        use_container_width=True,
    )
    payload = _try_load_json(diagnostics_text)
    if not isinstance(payload, dict):
        with st.expander("学术诊断预览", expanded=False):
            st.text(diagnostics_text)
        return

    overview = payload.get("overview") if isinstance(payload.get("overview"), dict) else {}
    cards = overview.get("cards") if isinstance(overview.get("cards"), list) else []
    average_score = overview.get("average_score", "-")
    critical_count = overview.get("critical_count", 0)
    warning_count = overview.get("warning_count", 0)
    summary_text = overview.get("summary") if isinstance(overview.get("summary"), str) else ""

    st.caption(
        f"学术诊断总览：平均分 {average_score}，critical {critical_count}，warning {warning_count}"
    )
    if summary_text:
        st.write(summary_text)

    if cards:
        cols = st.columns(min(3, len(cards)))
        for index, card in enumerate(cards):
            if not isinstance(card, dict):
                continue
            with cols[index % len(cols)]:
                label = card.get("label") if isinstance(card.get("label"), str) else card.get("key", "诊断项")
                severity = card.get("severity") if isinstance(card.get("severity"), str) else "info"
                score = card.get("score", 0)
                headline = card.get("headline") if isinstance(card.get("headline"), str) else ""
                st.markdown(f"**{label}**")
                st.caption(f"severity: {severity} · score: {score}")
                if headline:
                    st.write(headline)

    with st.expander("学术诊断详情", expanded=False):
        st.json(payload)


def _render_run_result(run: dict, *, show_success_header: bool, key_prefix: str) -> None:
    run_id = run.get("id") if isinstance(run.get("id"), str) else uuid.uuid4().hex
    output_path_raw = run.get("output_path") if isinstance(run.get("output_path"), str) else ""
    summary_path_raw = run.get("summary_path") if isinstance(run.get("summary_path"), str) else ""
    log_path_raw = run.get("log_path") if isinstance(run.get("log_path"), str) else ""
    diagnostics_path_raw = run.get("diagnostics_path") if isinstance(run.get("diagnostics_path"), str) else ""
    tables_path_raw = run.get("tables_path") if isinstance(run.get("tables_path"), str) else ""
    images_path_raw = run.get("images_path") if isinstance(run.get("images_path"), str) else ""
    model_output = run.get("model_output") if isinstance(run.get("model_output"), str) else ""
    run_status = run.get("status") if isinstance(run.get("status"), str) else ""
    run_error = run.get("error") if isinstance(run.get("error"), str) else ""

    output_path = Path(output_path_raw) if output_path_raw else None
    summary_path = Path(summary_path_raw) if summary_path_raw else None
    log_path = Path(log_path_raw) if log_path_raw else None
    diagnostics_path = Path(diagnostics_path_raw) if diagnostics_path_raw else None
    tables_path = Path(tables_path_raw) if tables_path_raw else None
    images_path = Path(images_path_raw) if images_path_raw else None

    if run_status and run_status != "success":
        st.warning(f"状态：{run_status}")
    if run_error:
        st.error(run_error)

    if output_path and output_path.exists():
        output_bytes = _safe_read_bytes(output_path)
        if output_bytes is None:
            st.error(f"读取输出文件失败：{output_path}")
        else:
            if show_success_header:
                st.success(f"审阅完成：{output_path.name}")
            col_dl, col_open = st.columns(2)
            with col_dl:
                st.download_button(
                    "下载修订文档",
                    data=output_bytes,
                    file_name=output_path.name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"{key_prefix}dl_doc_{run_id}",
                    use_container_width=True,
                )
            with col_open:
                if st.button(
                    "打开结果目录",
                    key=f"{key_prefix}open_dir_{run_id}",
                    use_container_width=True,
                ):
                    ok, error = _open_in_file_manager(output_path.parent)
                    if not ok:
                        st.error(f"打开目录失败：{error}")
    elif output_path_raw:
        st.warning(f"输出文件不存在：{output_path_raw}")

    if diagnostics_path and diagnostics_path.exists():
        if show_success_header and not (output_path and output_path.exists()):
            st.success(f"学术诊断完成：{diagnostics_path.name}")
        _render_diagnostics_result(diagnostics_path, run_id=run_id, key_prefix=key_prefix)
    elif diagnostics_path_raw:
        st.warning(f"学术诊断文件不存在：{diagnostics_path_raw}")

    if summary_path and summary_path.exists():
        summary_text = _safe_read_text(summary_path, encoding="utf-8")
        if summary_text is None:
            st.error(f"读取修订摘要失败：{summary_path}")
        else:
            st.download_button(
                "下载修订摘要(JSON)",
                data=summary_text,
                file_name=summary_path.name,
                mime="application/json",
                key=f"{key_prefix}dl_summary_{run_id}",
                use_container_width=True,
            )
            with st.expander("修订摘要预览", expanded=False):
                try:
                    st.json(json.loads(summary_text))
                except Exception:
                    st.text(summary_text)

    if log_path and log_path.exists():
        log_text = _safe_read_text(log_path, encoding="utf-8")
        if log_text is None:
            st.error(f"读取运行日志失败：{log_path}")
        else:
            with st.expander("运行日志(模型修改细节)", expanded=False):
                st.code(_tail_lines_text(log_text, _streamlit_log_tail_lines()))
            st.download_button(
                "下载运行日志",
                data=log_text,
                file_name=log_path.name,
                mime="text/plain",
                key=f"{key_prefix}dl_log_{run_id}",
                    use_container_width=True,
                )

    if tables_path and tables_path.exists():
        tables_text = _safe_read_text(tables_path, encoding="utf-8")
        if tables_text is None:
            st.error(f"读取表格提取结果失败：{tables_path}")
        else:
            st.download_button(
                "下载表格元素(JSON)",
                data=tables_text,
                file_name=tables_path.name,
                mime="application/json",
                key=f"{key_prefix}dl_tables_{run_id}",
                use_container_width=True,
            )
            with st.expander("表格元素预览", expanded=False):
                payload = _try_load_json(tables_text)
                if isinstance(payload, dict):
                    tables = payload.get("tables") if isinstance(payload.get("tables"), list) else []
                    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
                    errors = payload.get("errors") if isinstance(payload.get("errors"), list) else []
                    st.caption(f"表格数：{len(tables)}；warnings：{len(warnings)}；errors：{len(errors)}")
                    if errors:
                        st.error("\n".join(str(x) for x in errors[:8]))
                    if warnings:
                        with st.expander("warnings", expanded=False):
                            st.text("\n".join(str(x) for x in warnings[:20]))
                    images_dir_raw = payload.get("images_dir") if isinstance(payload.get("images_dir"), str) else ""
                    images_dir = Path(images_dir_raw) if images_dir_raw else None
                    if images_dir and images_dir.exists():
                        col_open, col_count = st.columns([1, 2])
                        with col_open:
                            if st.button("打开表格图片目录", key=f"{key_prefix}open_table_imgs_{run_id}"):
                                ok, error = _open_in_file_manager(images_dir)
                                if not ok:
                                    st.error(f"打开目录失败：{error}")
                        with col_count:
                            try:
                                img_files = sorted(
                                    [
                                        p
                                        for p in images_dir.iterdir()
                                        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff"}
                                    ],
                                    key=lambda p: p.name,
                                )
                            except Exception:
                                img_files = []
                            if img_files:
                                st.caption(f"已导出表格图片：{len(img_files)} 张（预览前 9 张）")
                                cols = st.columns(3)
                                for idx, img in enumerate(img_files[:9]):
                                    with cols[idx % 3]:
                                        st.image(str(img), caption=img.name, use_container_width=True)
                    # Quick preview of the first table when it is reasonably small.
                    if tables:
                        first = tables[0] if isinstance(tables[0], dict) else None
                        if isinstance(first, dict):
                            try:
                                rows = int(first.get("rows", 0) or 0)
                                cols = int(first.get("cols", 0) or 0)
                            except Exception:
                                rows, cols = 0, 0
                            if 1 <= rows <= 30 and 1 <= cols <= 10:
                                grid = [["" for _ in range(cols)] for _ in range(rows)]
                                cells = first.get("cells") if isinstance(first.get("cells"), list) else []
                                for cell in cells:
                                    if not isinstance(cell, dict):
                                        continue
                                    try:
                                        r = int(cell.get("row", 0) or 0)
                                        c = int(cell.get("col", 0) or 0)
                                    except Exception:
                                        continue
                                    if 1 <= r <= rows and 1 <= c <= cols:
                                        text = cell.get("text") if isinstance(cell.get("text"), str) else ""
                                        grid[r - 1][c - 1] = text
                                with st.expander("首个表格预览(文本)", expanded=False):
                                    st.table(grid)
                    with st.expander("原始 JSON", expanded=False):
                        st.json(payload)
                else:
                    st.text(tables_text[:4000] + ("…" if len(tables_text) > 4000 else ""))

    if images_path and images_path.exists():
        images_text = _safe_read_text(images_path, encoding="utf-8")
        if images_text is None:
            st.error(f"读取图片提取结果失败：{images_path}")
        else:
            st.download_button(
                "下载文档图片索引(JSON)",
                data=images_text,
                file_name=images_path.name,
                mime="application/json",
                key=f"{key_prefix}dl_images_{run_id}",
                use_container_width=True,
            )
            with st.expander("图片索引预览", expanded=False):
                payload = _try_load_json(images_text)
                if isinstance(payload, dict):
                    images = payload.get("images") if isinstance(payload.get("images"), list) else []
                    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
                    errors = payload.get("errors") if isinstance(payload.get("errors"), list) else []
                    st.caption(f"图片数：{len(images)}；warnings：{len(warnings)}；errors：{len(errors)}")
                    if errors:
                        st.error("\n".join(str(x) for x in errors[:8]))
                    if warnings:
                        with st.expander("warnings", expanded=False):
                            st.text("\n".join(str(x) for x in warnings[:20]))
                    images_dir_raw = payload.get("images_dir") if isinstance(payload.get("images_dir"), str) else ""
                    images_dir = Path(images_dir_raw) if images_dir_raw else None
                    if images_dir and images_dir.exists():
                        col_open, col_preview = st.columns([1, 2])
                        with col_open:
                            if st.button("打开图片目录", key=f"{key_prefix}open_doc_imgs_{run_id}"):
                                ok, error = _open_in_file_manager(images_dir)
                                if not ok:
                                    st.error(f"打开目录失败：{error}")
                        with col_preview:
                            try:
                                img_files = sorted(
                                    [
                                        p
                                        for p in images_dir.iterdir()
                                        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff"}
                                    ],
                                    key=lambda p: p.name,
                                )
                            except Exception:
                                img_files = []
                            if img_files:
                                st.caption(f"已导出图片：{len(img_files)} 张（预览前 9 张）")
                                cols = st.columns(3)
                                for idx, img in enumerate(img_files[:9]):
                                    with cols[idx % 3]:
                                        st.image(str(img), caption=img.name, use_container_width=True)
                    with st.expander("原始 JSON", expanded=False):
                        st.json(payload)
                else:
                    st.text(images_text[:4000] + ("…" if len(images_text) > 4000 else ""))

    if model_output:
        with st.expander("模型输出", expanded=False):
            st.write(model_output)


def main() -> None:
    st.set_page_config(page_title="学术文稿助手", layout="wide")
    st.title("学术文稿助手")

    settings = load_settings()
    workspace = _prepare_workspace(settings.root_dir)
    mode = st.sidebar.radio("功能模式", options=["智能校稿", "课题报告生成"], index=0)
    prev_mode = st.session_state.get(_MODE_KEY)
    if prev_mode != mode:
        st.session_state[_MODE_KEY] = mode
        if mode == "智能校稿":
            st.session_state.pop(_REPORT_LAST_RESULT_KEY, None)
        else:
            st.session_state.pop(_REPORT_LAST_RESULT_KEY, None)
    if mode == "课题报告生成":
        _render_report_ui(settings, workspace)
        return
    _init_chat_state(workspace, settings.persist_sessions)
    _apply_queued_widget_state()

    has_win32 = _has_win32()
    has_python_docx = _has_python_docx()
    zhengda_template_path = Path(settings.root_dir) / "templates" / "正大杯报告格式.dotx"
    has_zhengda_template = zhengda_template_path.exists()
    review_presets = list_review_presets()
    preset_map = {item["key"]: item for item in review_presets if isinstance(item, dict) and isinstance(item.get("key"), str)}
    preset_options = [item["key"] for item in review_presets if isinstance(item, dict) and isinstance(item.get("key"), str)]
    if not preset_options:
        preset_options = ["general_academic"]
        preset_map = {
            "general_academic": {
                "key": "general_academic",
                "label": "通用学术论文/综述",
                "description": "",
                "expert_view": BASE_EXPERT_VIEW,
                "default_constraints": list(BASE_CONSTRAINTS),
                "diagnostics_dimensions": [],
                "section_expectations": [],
            }
        }
    engine_options = ["auto"]
    if has_win32:
        engine_options.append("win32com")
    if has_python_docx:
        engine_options.append("python-docx")

    with st.sidebar:
        st.header("引擎与模型")
        preset_key = st.selectbox(
            "学术预设",
            options=preset_options,
            index=preset_options.index("general_academic") if "general_academic" in preset_options else 0,
            key=_REVIEW_PRESET_KEY,
            format_func=lambda key: preset_map.get(key, {}).get("label", key),
        )
        selected_preset = preset_map.get(preset_key, preset_map[preset_options[0]])
        preset_description = selected_preset.get("description") if isinstance(selected_preset.get("description"), str) else ""
        if preset_description:
            st.caption(preset_description)
        diagnostics_enabled = st.checkbox(
            "生成学术诊断",
            value=True,
            key=_REVIEW_DIAGNOSTICS_KEY,
            help="输出统一的 *.diagnostics.json，并在结果区展示结构化诊断卡片。",
        )
        diagnostics_only = st.checkbox(
            "仅做学术诊断，不生成修订文档",
            value=False,
            key=_REVIEW_DIAGNOSTICS_ONLY_KEY,
            disabled=not diagnostics_enabled,
        )
        if diagnostics_only and not diagnostics_enabled:
            diagnostics_enabled = True
        revision_engine = st.selectbox(
            "审阅引擎",
            options=engine_options,
            index=0,
            format_func=lambda x: {
                "auto": "自动(推荐)",
                "win32com": "Win32 Word",
                "python-docx": "python-docx",
            }.get(x, x),
        )
        model_override = st.text_input("模型覆盖(可选)", value="")
        try:
            from app.formatting.profiles import PROFILES  # noqa: WPS433

            format_all = [p.key for p in PROFILES]
        except Exception:
            format_all = ["none", "zhengda_cup"]

        format_options = ["none"]
        for key in format_all:
            if key == "none":
                continue
            if key == "zhengda_cup" and (not has_win32 or not has_zhengda_template):
                continue
            format_options.append(key)
        format_profile = st.selectbox(
            "排版风格",
            options=format_options,
            index=0,
            format_func=lambda x: {"none": "无", "zhengda_cup": "正大杯报告格式", "thesis_standard": "论文标准格式"}.get(x, x),
            help="在审阅输出生成后，对文档进行整体排版规范化（需要 Win32 Word）。",
            key=_FORMAT_PROFILE_SELECT_KEY,
        )
        auto_approve = st.checkbox("自动批准工具中断", value=True)
        if model_override:
            settings.model = model_override
        if (settings.model or "").strip().lower().startswith("openai:") and not _has_openai_key():
            st.error("未检测到 OPENAI_API_KEY/API_KEY，模型调用将失败；请先配置环境变量或 .env。")
        prefer_replace = st.checkbox(
            "自动修订(更积极直接改文)",
            value=False,
            help="开启后模型会更倾向输出 replace 指令并直接改写原文（Win32 Word 才能生成修订痕迹；python-docx 仍以红色建议为主）。",
        )
        expansion_level = st.selectbox(
            "扩充强度",
            options=["none", "light", "heavy"],
            index=0,
            format_func=lambda x: {"none": "不扩充", "light": "轻量扩充", "heavy": "大量扩充"}.get(x, x),
            help="选择是否扩充以及扩充幅度；轻量为少量补充，重度为显著扩写并增强衔接。",
        )
        allow_web_search = st.checkbox(
            "允许联网检索(扩充完善/核验)",
            value=False,
            help="启用后可调用 Tavily API 进行检索，请配置 TAVILY_API_KEY。",
        )
        allow_py_docx_fallback = st.checkbox(
            "允许python-docx兜底(建议以红色文字附在句子/段落后)",
            value=False,
        )
        comment_author = st.text_input("批注作者名称", value="呆塔大师兄")
        strip_existing_comments = st.checkbox(
            "开始审阅前删除原文批注",
            value=False,
            help="会在工作区副本上清空原文已有批注，避免旧批注与本次批注混在一起。",
        )
        st.subheader("上下文与记忆")
        memory_scope = st.selectbox(
            "记忆模式",
            options=["document", "run", "off", "session"],
            index=0,
            key=_MEMORY_SCOPE_KEY,
            format_func=lambda x: {
                "document": "按文档(跨次审阅·推荐)",
                "run": "仅本次(跨分段)",
                "off": "关闭(每段独立·最快)",
                "session": "会话(所有文档共享)",
            }.get(x, x),
            help=(
                "按文档/会话会将审阅上下文持久化到 workspace/agent_state/checkpoints.sqlite，用于跨段落/跨次审阅保持一致性。"
                "文档模式会优先使用文档内置的稳定 ID（自定义属性）以便跨修订版保持记忆。"
                "启用记忆时会自动关闭并行分段审阅以保证上下文一致。"
            ),
        )
        inline_context = st.selectbox(
            "上下文行(内联)",
            options=["boundary", "none", "all"],
            index=0,
            key=_INLINE_CONTEXT_KEY,
            format_func=lambda x: {
                "boundary": "仅首/尾段落(推荐)",
                "none": "不内联(最省 token)",
                "all": "每段都带相邻上下文(最耗 token)",
            }.get(x, x),
            help="控制 CTX_PREV/CTX_NEXT 的插入方式，用于减少重复上下文占用模型窗口。",
        )
        chunk_context = st.slider(
            "跨段上下文(段落数)",
            min_value=0,
            max_value=10,
            value=2,
            key=_CHUNK_CONTEXT_KEY,
            help="每个分段在前后额外附带的参考段落数（CTX_ONLY）。0 表示完全不附带。",
        )
        ctx_max_chars = st.number_input(
            "上下文截断(字符,0=不截断)",
            min_value=0,
            max_value=4000,
            value=1200,
            step=100,
            key=_CTX_MAX_CHARS_KEY,
            help="仅截断 CTX_* 参考段落，正文目标段落不截断；用于腾出更多上下文窗口。",
        )
        if memory_scope != "off":
            st.caption("已启用记忆：将使用稳定 thread_id，并自动关闭并行分段审阅（更稳、更能利用上下文）。")
            if settings.persist_sessions and settings.checkpoint_path and _has_langgraph_sqlite():
                try:
                    cp_path = resolve_path(settings.checkpoint_path)
                except Exception:
                    cp_path = None
                if cp_path is not None:
                    st.caption(f"持久化存储：{cp_path}")
            else:
                st.warning("未检测到 sqlite checkpointer：记忆可能无法落盘（建议安装/升级 langgraph）。")

        st.subheader("表格/图片提取")
        extract_docx_images = st.checkbox(
            "提取文档图片(全局)",
            value=False,
            key=_DOCX_IMAGE_EXTRACT_KEY,
            help="输出 .images.json 和 *_images 目录：导出 docx 包中 word/media 的所有图片，并尝试补齐形状/图表等渲染图（需 Win32 Word）。",
        )
        table_extract_available = bool(has_win32 or has_python_docx)
        extract_tables = st.checkbox(
            "提取表格元素(JSON)",
            value=False,
            key=_TABLE_EXTRACT_KEY,
            disabled=not table_extract_available,
            help="输出 .tables.json：包含表格单元格文本、合并信息、表格内图片文件路径（优先 Win32 Word；无 Word 时 python-docx 兜底）。",
        )
        has_apiyi_key = _has_apiyi_key()
        analyze_table_images = st.checkbox(
            "表格图片理解(APIYI)",
            value=False,
            key=_TABLE_IMAGE_UNDERSTANDING_KEY,
            disabled=(not table_extract_available) or (not has_apiyi_key),
            help="启用后会导出表格图片并调用图片理解智能体；需配置 APIYI_API_KEY。",
        )
        if not table_extract_available:
            st.caption("未检测到 Win32 Word 或 python-docx，已禁用表格解析。")
        elif not has_win32 and has_python_docx:
            st.caption("未检测到 Win32 Word（pywin32），将使用 python-docx 兜底解析（对浮动图形/图表支持有限）。")
        elif not has_apiyi_key:
            st.caption("未检测到 APIYI_API_KEY，已禁用图片理解。")
        image_prompt = st.text_input(
            "图片理解提示词",
            value="描述分析这张图",
            key=_TABLE_IMAGE_PROMPT_KEY,
            disabled=not analyze_table_images,
        )
        parallel_disabled = memory_scope != "off"
        parallel_review = st.checkbox(
            "并行分段审阅(长文档推荐)",
            value=False if parallel_disabled else True,
            disabled=parallel_disabled,
        )
        parallel_workers = st.slider(
            "并行线程数",
            min_value=1,
            max_value=8,
            value=4,
            disabled=not parallel_review,
        )
        chunk_size = st.slider("每段最大段落数", min_value=10, max_value=80, value=40)
        parallel_min_paragraphs = st.number_input(
            "并行启用阈值(段落数)",
            min_value=1,
            max_value=1000,
            value=80,
            step=10,
        )
        has_tavily_key = _has_tavily_key()
        allow_expansion = expansion_level != "none"
        allow_web_search_effective = allow_web_search
        if allow_expansion:
            if has_tavily_key and not allow_web_search:
                st.caption("已选择扩充，自动启用联网检索以获取补充信息。")
                allow_web_search_effective = True
            elif not has_tavily_key and not allow_web_search:
                st.warning("已选择扩充，但未配置 TAVILY_API_KEY，无法联网检索。")
        if not has_python_docx:
            st.caption("未检测到 python-docx 依赖，已隐藏该选项。")
        if not has_win32 and not has_python_docx:
            st.error("未检测到可用审阅引擎，请安装 pywin32 或 python-docx。")
        if format_profile != "none" and not has_win32:
            st.error("当前未检测到 Win32 Word（pywin32），无法应用排版风格。请安装 pywin32 并确保本机有 Word。")
        if has_win32 and not has_zhengda_template:
            st.warning(f"未找到模板：{zhengda_template_path}（可先运行 tools/create_zhengda_cup_template.py 生成）")
        with st.expander("预设说明", expanded=False):
            section_expectations = (
                selected_preset.get("section_expectations")
                if isinstance(selected_preset.get("section_expectations"), list)
                else []
            )
            diagnostics_dimensions = (
                selected_preset.get("diagnostics_dimensions")
                if isinstance(selected_preset.get("diagnostics_dimensions"), list)
                else []
            )
            sample_use_cases = (
                selected_preset.get("sample_use_cases")
                if isinstance(selected_preset.get("sample_use_cases"), list)
                else []
            )
            if diagnostics_dimensions:
                st.write("诊断维度：")
                for item in diagnostics_dimensions:
                    st.write(f"- {item}")
            if section_expectations:
                st.write("重点章节：")
                for item in section_expectations:
                    if isinstance(item, dict):
                        label = item.get("label") if isinstance(item.get("label"), str) else item.get("key", "")
                        st.write(f"- {label}")
            if sample_use_cases:
                st.write("适用场景：")
                for item in sample_use_cases:
                    if isinstance(item, str) and item.strip():
                        st.write(f"- {item.strip()}")

        st.divider()
        st.header("聊天会话")
        sessions = st.session_state.get(_CHAT_SESSIONS_KEY)
        if not isinstance(sessions, list):
            sessions = []
        session_ids: list[str] = []
        session_labels: dict[str, str] = {}
        for session in sessions:
            if not isinstance(session, dict):
                continue
            session_id = session.get("id")
            if not isinstance(session_id, str) or not session_id:
                continue
            title = session.get("title") if isinstance(session.get("title"), str) else session_id
            runs = session.get("runs")
            run_count = len(runs) if isinstance(runs, list) else 0
            updated_at = session.get("updated_at") if isinstance(session.get("updated_at"), str) else ""
            label = f"{title} ({run_count})"
            if updated_at:
                label = f"{label} · {updated_at}"
            session_ids.append(session_id)
            session_labels[session_id] = label
        if not session_ids:
            session = _new_chat_session()
            sessions = [session]
            st.session_state[_CHAT_SESSIONS_KEY] = sessions
            st.session_state[_CHAT_ACTIVE_SESSION_KEY] = session["id"]
            st.session_state[_CHAT_SESSION_SELECT_KEY] = session["id"]
            _persist_chat_state(settings.persist_sessions)
            session_ids = [session["id"]]
            session_labels = {session["id"]: f"{session.get('title')} (0) · {session.get('updated_at')}"}

        selected_session_id = st.selectbox(
            "选择会话",
            options=session_ids,
            format_func=lambda value: session_labels.get(value, value),
            key=_CHAT_SESSION_SELECT_KEY,
        )
        if isinstance(selected_session_id, str) and selected_session_id != st.session_state.get(_CHAT_ACTIVE_SESSION_KEY):
            st.session_state[_CHAT_ACTIVE_SESSION_KEY] = selected_session_id
            _persist_chat_state(settings.persist_sessions)

        active_session = _get_active_session()
        active_session_id = active_session.get("id") if active_session and isinstance(active_session.get("id"), str) else ""
        title_input_key = f"{_CHAT_SESSION_TITLE_INPUT_PREFIX}_{active_session_id}" if active_session_id else ""
        if active_session and title_input_key:
            title_value = active_session.get("title") if isinstance(active_session.get("title"), str) else ""
            title_input = st.text_input("会话名称", value=title_value, key=title_input_key)
            if title_input and title_input != title_value:
                active_session["title"] = title_input
                active_session["updated_at"] = _now_iso()
                _persist_chat_state(settings.persist_sessions)

        col_session_a, col_session_b = st.columns(2)
        with col_session_a:
            if st.button("新建会话", use_container_width=True):
                new_session = _new_chat_session()
                sessions.append(new_session)
                st.session_state[_CHAT_SESSIONS_KEY] = sessions
                st.session_state[_CHAT_ACTIVE_SESSION_KEY] = new_session["id"]
                _queue_widget_state(_CHAT_SESSION_SELECT_KEY, new_session["id"])
                st.session_state[f"{_CHAT_SESSION_TITLE_INPUT_PREFIX}_{new_session['id']}"] = new_session["title"]
                _persist_chat_state(settings.persist_sessions)
                _rerun()
        with col_session_b:
            if st.button("删除会话", use_container_width=True, disabled=len(session_ids) <= 1):
                delete_id = st.session_state.get(_CHAT_ACTIVE_SESSION_KEY)
                if isinstance(delete_id, str):
                    remaining = [s for s in sessions if isinstance(s, dict) and s.get("id") != delete_id]
                    st.session_state[_CHAT_SESSIONS_KEY] = remaining
                    fallback_id = next(
                        (s.get("id") for s in remaining if isinstance(s, dict) and isinstance(s.get("id"), str)),
                        None,
                    )
                    if not isinstance(fallback_id, str) or not fallback_id:
                        new_session = _new_chat_session()
                        remaining.append(new_session)
                        fallback_id = new_session["id"]
                    st.session_state[_CHAT_ACTIVE_SESSION_KEY] = fallback_id
                    _queue_widget_state(_CHAT_SESSION_SELECT_KEY, fallback_id)
                    _persist_chat_state(settings.persist_sessions)
                    _rerun()

        if active_session and st.button("清空当前会话记录", use_container_width=True):
            active_session["runs"] = []
            active_session["updated_at"] = _now_iso()
            _persist_chat_state(settings.persist_sessions)
            _rerun()

    col_left, col_right = st.columns([2, 1])
    with col_left:
        uploaded = st.file_uploader("上传 Word 文件(.docx/.docm/.dotx/.dotm)", type=["docx", "docm", "dotx", "dotm"])
        preset_expert_view = (
            selected_preset.get("expert_view")
            if isinstance(selected_preset.get("expert_view"), str) and selected_preset.get("expert_view")
            else BASE_EXPERT_VIEW
        )
        preset_default_constraints = (
            selected_preset.get("default_constraints")
            if isinstance(selected_preset.get("default_constraints"), list)
            else list(BASE_CONSTRAINTS)
        )
        st.markdown(f"**审阅角色：** {preset_expert_view}")
        prompt_dir = _resolve_prompt_dir(settings.root_dir)
        prompt_files = _list_prompt_files(prompt_dir) if prompt_dir else []
        prompt_placeholder = "（不使用预置提示词）"
        prompt_map = {p.name: p for p in prompt_files}
        prompt_options = [prompt_placeholder] + list(prompt_map.keys()) if prompt_map else [prompt_placeholder]
        current_prompt_choice = st.session_state.get(_INTENT_PROMPT_SELECT_KEY)
        if (
            isinstance(current_prompt_choice, str)
            and current_prompt_choice
            and current_prompt_choice not in prompt_options
        ):
            st.session_state[_INTENT_PROMPT_SELECT_KEY] = prompt_placeholder
        selected_prompt = st.selectbox(
            "快捷提示词(可选)",
            options=prompt_options,
            index=0,
            key=_INTENT_PROMPT_SELECT_KEY,
            help=f"从 {prompt_dir} 加载" if prompt_dir else "未找到 prompt 目录",
        )
        selected_prompt_path = prompt_map.get(selected_prompt)
        selected_prompt_text = (
            _safe_read_text(selected_prompt_path, encoding="utf-8-sig") if selected_prompt_path else None
        )
        col_fill, col_append = st.columns(2)
        with col_fill:
            if st.button(
                "一键填入",
                use_container_width=True,
                disabled=not bool(selected_prompt_text),
            ):
                _queue_widget_state(_INTENT_INPUT_KEY, selected_prompt_text or "")
                _rerun()
        with col_append:
            if st.button(
                "追加填入",
                use_container_width=True,
                disabled=not bool(selected_prompt_text),
            ):
                existing_intent = st.session_state.get(_INTENT_INPUT_KEY, "")
                existing_intent = existing_intent if isinstance(existing_intent, str) else ""
                new_intent = existing_intent
                if new_intent and selected_prompt_text:
                    new_intent = f"{new_intent.rstrip()}\n\n{selected_prompt_text.lstrip()}"
                elif selected_prompt_text:
                    new_intent = selected_prompt_text
                _queue_widget_state(_INTENT_INPUT_KEY, new_intent)
                _rerun()
        if selected_prompt_text:
            with st.expander("提示词预览", expanded=False):
                st.code(selected_prompt_text)

        intent = st.text_area(
            "审阅目标/需求",
            placeholder="说明需要改进或检查的内容",
            key=_INTENT_INPUT_KEY,
        )
        focus_only = st.checkbox(
            "仅审阅意图中提到的段落/标题(聚焦模式)",
            value=False,
            key=_FOCUS_FILTER_KEY,
            help="开启后，会自动识别你在意图中提到的“第X段/第X章/标题关键词/引用标题”，并只审阅这些位置；关闭则默认全文审阅。",
        )
        if focus_only:
            st.warning("已开启聚焦模式：本次将只审阅你在“审阅目标/需求”中明确提到的段落/章节/标题。")
        st.markdown("**默认约束：**")
        for item in preset_default_constraints:
            if isinstance(item, str) and item.strip():
                st.write(f"- {item}")
        extra_constraints = st.text_area(
            "附加约束(可选，每行一条)",
            placeholder="在此补充额外约束...",
        )

    latest_placeholder = None
    with col_right:
        st.subheader("执行")
        if revision_engine == "python-docx":
            st.info("最终输出：正文中附带红色修改建议的Word文档。")
        else:
            st.info("最终输出：带修订痕迹与批注的Word文档。")
        with st.expander("审阅检查清单", expanded=False):
            if revision_engine == "python-docx":
                st.write("- 红色修改建议是否贴合对应句子/段落")
            else:
                st.write("- 修订痕迹与批注是否完整显示")
            st.write("- 仅审阅正文段落，图表/图注/表注不应出现批注")
            st.write("- 每处修改都有明确原因，涉及多句时逐句说明")
            st.write("- 不做无依据扩写或口吻改写")
            st.write("- 不对空格/标点等格式微调给批注，重点审阅逻辑与表达")
            st.write("- 事实与数字未被无依据改动")
        with st.expander("审批流程提示", expanded=False):
            st.write("- 关键工具调用会触发审批（可启用自动审批）")
            st.write("- 若未开启自动审批，需在日志中处理批准/编辑/拒绝")
            st.write("- 建议在正式交付前人工复核修订摘要与批注")
        with st.expander("修订摘要 JSON 模板", expanded=False):
            st.code(SUMMARY_TEMPLATE, language="json")
        run_button = st.button("开始审阅", type="primary", use_container_width=True)
        status = st.empty()
        st.divider()
        st.subheader("最近一次结果")
        latest_placeholder = st.container()

    should_run = bool(run_button)
    if run_button:
        if not uploaded:
            status.error("请上传 Word 文件（.docx/.docm/.dotx/.dotm）。")
            should_run = False
        if not intent and not diagnostics_only:
            status.error("请输入审阅目标/需求。")
            should_run = False
        if not has_win32 and not has_python_docx:
            status.error("当前未检测到可用审阅引擎，请先安装 pywin32 或 python-docx。")
            should_run = False
        if revision_engine == "python-docx" and not diagnostics_only:
            st.warning("python-docx 无法写入Word原生批注，建议会以红色文字附在句子/段落后。")
        if revision_engine == "auto" and not has_win32 and not allow_py_docx_fallback and not diagnostics_only:
            status.error("自动模式无法使用win32com时将失败；请安装pywin32，或改选python-docx并接受红色建议附在句子/段落后。")
            should_run = False

        if should_run:
            input_path = _save_upload(uploaded, workspace)
            output_path = _build_output_path(uploaded.name, input_path.parent)

            extract_tables_effective = bool(extract_tables or analyze_table_images)
            os.environ["ALLOW_PYTHON_DOCX_FALLBACK"] = "true" if allow_py_docx_fallback else "false"
            os.environ["COMMENT_AUTHOR"] = comment_author
            os.environ["STRIP_EXISTING_COMMENTS"] = "true" if strip_existing_comments else "false"
            os.environ["REVIEW_PREFER_REPLACE"] = "true" if prefer_replace else "false"
            os.environ["ENABLE_WEB_SEARCH"] = "true" if allow_web_search_effective else "false"
            os.environ["REVIEW_ENABLE_FOCUS_FILTER"] = "true" if focus_only else "false"
            os.environ["REVIEW_MEMORY_SCOPE"] = (memory_scope or "document").strip()
            os.environ["REVIEW_INLINE_CONTEXT"] = (inline_context or "boundary").strip()
            os.environ["REVIEW_CHUNK_CONTEXT"] = str(int(chunk_context))
            os.environ["REVIEW_CONTEXT_MAX_CHARS"] = str(int(ctx_max_chars))
            os.environ["EXTRACT_DOCX_IMAGES"] = "true" if extract_docx_images else "false"
            os.environ["EXTRACT_TABLE_ELEMENTS"] = "true" if extract_tables_effective else "false"
            os.environ["TABLE_IMAGE_UNDERSTANDING"] = "true" if analyze_table_images else "false"
            os.environ["TABLE_IMAGE_PROMPT"] = (image_prompt or "描述分析这张图").strip()
            os.environ["REVIEW_PARALLEL"] = "true" if parallel_review else "false"
            os.environ["REVIEW_PARALLEL_WORKERS"] = str(parallel_workers)
            os.environ["REVIEW_SECTION_CHUNK_SIZE"] = str(chunk_size)
            os.environ["REVIEW_PARALLEL_MIN_PARAGRAPHS"] = str(parallel_min_paragraphs)
            settings.revision_engine = revision_engine
        settings.auto_approve = auto_approve
        settings.format_profile = format_profile

        constraints = _parse_extra_constraints(extra_constraints)
        resolved_expert_view, resolved_format_profile, merged_constraints = apply_preset_defaults(
            preset_key,
            expert_view="",
            format_profile=format_profile,
            constraints=constraints,
        )
        settings.format_profile = resolved_format_profile

        status.info("正在执行学术审阅...")
        run_status = "success"
        run_error = ""
        diagnostics_path = output_path.with_suffix(".diagnostics.json")
        try:
            if diagnostics_only:
                result = {}
            else:
                result = run_revision(
                    settings=settings,
                    input_path=str(input_path),
                    output_path=str(output_path),
                    intent=intent,
                    expert_view=resolved_expert_view,
                    constraints=merged_constraints,
                    allow_expansion=allow_expansion,
                    expansion_level=expansion_level,
                    allow_web_search=allow_web_search_effective,
                )
            if diagnostics_enabled:
                diagnostics_path = write_review_diagnostics(
                    input_path=str(input_path),
                    output_path=str(output_path),
                    preset_key=preset_key,
                )
        except RuntimeError as exc:
            run_status = "failed"
            run_error = str(exc)
            status.error(run_error)
            result = {}
        except Exception as exc:  # noqa: BLE001
            run_status = "failed"
            run_error = f"审阅失败：{exc}"
            status.error(run_error)
            result = {}
        else:
            if diagnostics_only:
                status.success("学术诊断完成。")
            else:
                status.success("审阅完成。")

        summary_path = output_path.with_suffix(".summary.json")
        log_path = output_path.with_suffix(".log.txt")
        tables_path = output_path.with_suffix(".tables.json")
        images_path = output_path.with_suffix(".images.json")
        model_output = ""
        if isinstance(result, dict) and result.get("messages"):
            last = result["messages"][-1]
            content = getattr(last, "content", None)
            model_output = content if content is not None else str(last)

        run_record = {
            "id": uuid.uuid4().hex,
            "created_at": _now_iso(),
            "input_file": uploaded.name,
            "preset_key": preset_key,
            "preset_label": selected_preset.get("label", preset_key),
            "engine": revision_engine,
            "format_profile": format_profile,
            "strip_existing_comments": bool(strip_existing_comments),
            "focus_only": bool(focus_only),
            "allow_expansion": bool(allow_expansion),
            "expansion_level": expansion_level,
            "allow_web_search": bool(allow_web_search_effective),
            "memory_scope": memory_scope,
            "extract_images": bool(extract_docx_images),
            "extract_tables": bool(extract_tables or analyze_table_images),
            "table_image_understanding": bool(analyze_table_images),
            "diagnostics": bool(diagnostics_enabled),
            "diagnostics_only": bool(diagnostics_only),
            "intent": intent,
            "constraints": merged_constraints,
            "status": run_status,
            "error": run_error,
            "output_path": str(output_path) if output_path.exists() else "",
            "summary_path": str(summary_path) if (summary_path.exists() and not diagnostics_only) else "",
            "log_path": str(log_path) if log_path.exists() else "",
            "diagnostics_path": str(diagnostics_path) if (diagnostics_enabled and diagnostics_path.exists()) else "",
            "tables_path": str(tables_path) if tables_path.exists() else "",
            "images_path": str(images_path) if images_path.exists() else "",
            "model_output": model_output,
        }

        active_session = _get_active_session()
        if active_session is not None:
            needs_rerun = False
            runs_list = active_session.get("runs")
            if not isinstance(runs_list, list):
                runs_list = []
                active_session["runs"] = runs_list
            runs_list.append(run_record)
            active_session["updated_at"] = _now_iso()
            if (
                isinstance(active_session.get("title"), str)
                and active_session["title"].startswith("会话 ")
                and len(runs_list) == 1
            ):
                new_title = f"{Path(uploaded.name).name} · {intent[:20]}".strip()
                active_session["title"] = new_title
                title_key = f"{_CHAT_SESSION_TITLE_INPUT_PREFIX}_{active_session['id']}"
                _queue_widget_state(title_key, new_title)
                needs_rerun = True
            _persist_chat_state(settings.persist_sessions)
            if needs_rerun:
                _rerun()

    active_session = _get_active_session()
    latest_run = None
    if active_session and isinstance(active_session.get("runs"), list) and active_session["runs"]:
        latest_run = active_session["runs"][-1] if isinstance(active_session["runs"][-1], dict) else None
    with latest_placeholder:
        if latest_run:
            _render_run_result(latest_run, show_success_header=False, key_prefix="latest_")
        else:
            st.caption("暂无运行结果。")

    st.divider()
    st.subheader("聊天记录")
    runs: list[dict] = []
    if active_session and isinstance(active_session.get("runs"), list):
        runs = [run for run in active_session["runs"] if isinstance(run, dict)]
    if not runs:
        st.caption("暂无记录。运行一次审阅后会在这里以聊天会话形式保留历史结果（点击下载不会清空）。")
        return

    for run in runs:
        created_at = run.get("created_at") if isinstance(run.get("created_at"), str) else ""
        input_file = run.get("input_file") if isinstance(run.get("input_file"), str) else ""
        preset_label = run.get("preset_label") if isinstance(run.get("preset_label"), str) else ""
        intent_text = run.get("intent") if isinstance(run.get("intent"), str) else ""
        engine = run.get("engine") if isinstance(run.get("engine"), str) else ""
        fmt = run.get("format_profile") if isinstance(run.get("format_profile"), str) else ""
        constraints = run.get("constraints") if isinstance(run.get("constraints"), list) else []
        stripped_comments = run.get("strip_existing_comments")
        allow_expansion_flag = run.get("allow_expansion")
        expansion_level_flag = run.get("expansion_level")
        allow_web_search_flag = run.get("allow_web_search")
        diagnostics_flag = run.get("diagnostics")
        diagnostics_only_flag = run.get("diagnostics_only")

        def _render_user() -> None:
            if created_at:
                st.markdown(f"**时间：** {created_at}")
            if input_file:
                st.markdown(f"**文件：** {Path(input_file).name}")
            if preset_label:
                st.markdown(f"**学术预设：** {preset_label}")
            if engine:
                st.markdown(f"**引擎：** {engine}")
            if fmt and fmt != "none":
                st.markdown(f"**排版风格：** { {'zhengda_cup': '正大杯报告格式'}.get(fmt, fmt) }")
            if isinstance(stripped_comments, bool):
                st.markdown(f"**原文批注：** {'已删除' if stripped_comments else '保留'}")
            if isinstance(diagnostics_only_flag, bool) and diagnostics_only_flag:
                st.markdown("**运行模式：** 仅学术诊断")
            elif isinstance(diagnostics_flag, bool):
                st.markdown(f"**学术诊断：** {'开启' if diagnostics_flag else '关闭'}")
            if isinstance(expansion_level_flag, str):
                label = {"none": "不扩充", "light": "轻量扩充", "heavy": "大量扩充"}.get(
                    expansion_level_flag, expansion_level_flag
                )
                st.markdown(f"**扩充强度：** {label}")
            elif isinstance(allow_expansion_flag, bool):
                st.markdown(f"**扩充完善：** {'允许' if allow_expansion_flag else '不允许'}")
            if isinstance(allow_web_search_flag, bool):
                st.markdown(f"**联网检索：** {'允许' if allow_web_search_flag else '不允许'}")
            if intent_text:
                st.markdown("**审阅目标/需求：**")
                st.write(intent_text)
            if constraints:
                with st.expander("附加约束", expanded=False):
                    for item in constraints:
                        if isinstance(item, str) and item.strip():
                            st.write(f"- {item.strip()}")

        _render_chat_message("user", _render_user)

        def _render_assistant() -> None:
            _render_run_result(run, show_success_header=True, key_prefix="history_")

        _render_chat_message("assistant", _render_assistant)


if __name__ == "__main__":
    os.environ.setdefault("AGENT_ROOT_DIR", str(Path(__file__).resolve().parent))
    main()
