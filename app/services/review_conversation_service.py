from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any

from app.agents.supervisor import build_agent
from app.services.preset_service import get_review_preset
from app.services.review_conversation_store import ReviewConversationStore
from app.services.review_service import ReviewRequest, create_review_run
from app.services.run_store import RunStore
from app.settings import load_settings
from app.tools.doc_map import build_indexed_sections


_DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_ALLOWED_SUFFIXES = {".docx", ".docm", ".dotx", ".dotm"}
_BOOL_KEYS = {
    "auto_approve",
    "allow_python_docx_fallback",
    "strip_existing_comments",
    "prefer_replace",
    "allow_expansion",
    "allow_web_search",
    "focus_only",
    "extract_docx_images",
    "extract_tables",
    "table_image_understanding",
    "parallel_review",
    "diagnostics",
}
_INT_KEYS = {
    "chunk_context",
    "context_max_chars",
    "parallel_workers",
    "chunk_size",
    "parallel_min_paragraphs",
}
_STR_KEYS = {
    "expert_view",
    "revision_engine",
    "format_profile",
    "expansion_level",
    "inline_context",
    "table_image_prompt",
    "comment_author",
    "model_override",
}


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w.\-\u4e00-\u9fff]+", "_", Path(name or "").name).strip("._")
    return cleaned or "document.docx"


def _validate_docx_filename(filename: str) -> str:
    safe_name = _safe_filename(filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise ValueError("Only .docx/.docm/.dotx/.dotm files are supported")
    return safe_name


def normalize_review_options(raw: dict[str, Any] | None) -> dict[str, Any]:
    payload = raw or {}
    options: dict[str, Any] = {}
    constraints = payload.get("constraints", payload.get("constraints_json", []))
    if isinstance(constraints, str):
        try:
            parsed = json.loads(constraints)
        except Exception:
            parsed = constraints.splitlines()
        constraints = parsed
    if isinstance(constraints, list):
        options["constraints"] = [str(item).strip() for item in constraints if str(item).strip()]
    else:
        options["constraints"] = []
    for key in _BOOL_KEYS:
        if key in payload:
            value = payload.get(key)
            if isinstance(value, str):
                options[key] = value.strip().lower() in {"1", "true", "yes", "on"}
            else:
                options[key] = bool(value)
    for key in _INT_KEYS:
        if key in payload and payload.get(key) not in {None, ""}:
            try:
                options[key] = int(payload.get(key))
            except Exception:
                continue
    for key in _STR_KEYS:
        if key in payload and payload.get(key) is not None:
            options[key] = str(payload.get(key)).strip()
    return options


def build_conversation_defaults(raw: dict[str, Any] | None, *, preset_key: str) -> dict[str, Any]:
    options = normalize_review_options(raw)
    options.setdefault("constraints", [])
    options.setdefault("expert_view", "")
    options.setdefault("revision_engine", "auto")
    options.setdefault("format_profile", "none")
    options.setdefault("allow_python_docx_fallback", False)
    options.setdefault("strip_existing_comments", False)
    options.setdefault("prefer_replace", False)
    options.setdefault("allow_expansion", False)
    options.setdefault("expansion_level", "none")
    options.setdefault("allow_web_search", False)
    options.setdefault("focus_only", False)
    options.setdefault("inline_context", "boundary")
    options.setdefault("chunk_context", 2)
    options.setdefault("context_max_chars", 1200)
    options.setdefault("extract_docx_images", False)
    options.setdefault("extract_tables", False)
    options.setdefault("table_image_understanding", False)
    options.setdefault("table_image_prompt", "Describe the figure for academic review.")
    options.setdefault("parallel_review", True)
    options.setdefault("parallel_workers", 4)
    options.setdefault("chunk_size", 40)
    options.setdefault("parallel_min_paragraphs", 80)
    options.setdefault("comment_author", "Reviewer")
    options.setdefault("model_override", "")
    options.setdefault("diagnostics", True)
    options["preset_key"] = preset_key
    return options


def create_review_conversation(
    conversation_store: ReviewConversationStore,
    *,
    filename: str,
    file_bytes: bytes,
    title: str,
    preset_key: str,
    defaults: dict[str, Any],
) -> dict:
    safe_name = _validate_docx_filename(filename)
    resolved_title = (title or "").strip() or Path(safe_name).stem or "Untitled"
    preset = get_review_preset(preset_key)
    assistant_message = (
        f"文稿已载入，当前预设为“{preset.label}”。你可以先提问，也可以直接发送修改要求。"
    )
    return conversation_store.create_conversation(
        title=resolved_title,
        input_filename=safe_name,
        preset_key=preset.key,
        defaults=build_conversation_defaults(defaults, preset_key=preset.key),
        original_filename=safe_name,
        original_bytes=file_bytes,
        content_type=_DOCX_CONTENT_TYPE,
        assistant_message=assistant_message,
    )


def _conversation_run_ids(conversation: dict) -> set[str]:
    values = {str(item.get("run_id")) for item in conversation.get("versions", []) if item.get("run_id")}
    head_run_id = (conversation.get("head_run_id") or "").strip()
    if head_run_id:
        values.add(head_run_id)
    return values


def resolve_conversation_base(
    conversation_store: ReviewConversationStore,
    run_store: RunStore,
    conversation_id: str,
    *,
    base_source: str,
    base_run_id: str = "",
) -> dict[str, Any]:
    conversation = conversation_store.get_internal_conversation(conversation_id)
    if conversation is None:
        raise KeyError(conversation_id)

    source = (base_source or "latest").strip().lower() or "latest"
    requested_run_id = (base_run_id or "").strip()
    if source not in {"latest", "original", "run"}:
        source = "latest"

    if source == "original":
        artifact = dict(conversation["original_artifact"])
        return {
            "source": "original",
            "run_id": "",
            "artifact_name": artifact["name"],
            "label": "原稿",
            "path": Path(artifact["path"]),
            "filename": artifact["filename"],
        }

    if source == "latest":
        latest_run_id = (conversation.get("head_run_id") or "").strip()
        if not latest_run_id:
            return resolve_conversation_base(conversation_store, run_store, conversation_id, base_source="original")
        artifact = run_store.get_artifact(latest_run_id, "revised_docx")
        if artifact is None:
            return resolve_conversation_base(conversation_store, run_store, conversation_id, base_source="original")
        return {
            "source": "latest",
            "run_id": latest_run_id,
            "artifact_name": artifact["name"],
            "label": f"V{conversation.get('head_version_no') or 0}",
            "path": Path(artifact["path"]),
            "filename": artifact["filename"],
        }

    if not requested_run_id:
        raise ValueError("base_run_id is required when base_source=run")
    if requested_run_id not in _conversation_run_ids(conversation):
        raise ValueError("The selected base run is not part of this conversation")
    artifact = run_store.get_artifact(requested_run_id, "revised_docx")
    if artifact is None:
        raise ValueError("The selected base run has no revised document")
    version_no = 0
    for item in conversation.get("versions", []):
        if item.get("run_id") == requested_run_id:
            version_no = int(item.get("version_no") or 0)
            break
    return {
        "source": "run",
        "run_id": requested_run_id,
        "artifact_name": artifact["name"],
        "label": f"V{version_no}" if version_no else requested_run_id,
        "path": Path(artifact["path"]),
        "filename": artifact["filename"],
    }


def _load_json_if_exists(path: str) -> dict[str, Any] | None:
    raw = (path or "").strip()
    if not raw:
        return None
    file_path = Path(raw)
    if not file_path.exists():
        return None
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _summarize_document(path: Path) -> str:
    sections = build_indexed_sections(str(path))
    lines: list[str] = []
    for section in sections:
        title = (section.title or "").strip()
        if title and title != "Document":
            lines.append(f"- {title}")
        for paragraph in section.paragraphs[:2]:
            text = (paragraph.text or "").strip()
            if not text:
                continue
            clipped = text[:220] + ("..." if len(text) > 220 else "")
            lines.append(f"  {clipped}")
        if len(lines) >= 18:
            break
    return "\n".join(lines[:18]).strip()


def _recent_messages_text(messages: list[dict], *, limit: int = 8) -> str:
    rendered: list[str] = []
    for item in messages[-limit:]:
        role = "用户" if item.get("role") == "user" else "助手"
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        rendered.append(f"{role}: {content[:300]}")
    return "\n".join(rendered)


def _message_text(result: dict) -> str:
    messages = result.get("messages") if isinstance(result, dict) else None
    if not messages:
        return ""
    last = messages[-1]
    content = getattr(last, "content", "")
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part).strip()
    return str(content or "").strip()


def generate_conversation_reply(
    conversation: dict,
    *,
    base: dict[str, Any],
    prompt: str,
    run_store: RunStore,
) -> str:
    settings = load_settings()
    defaults = conversation.get("defaults", {})
    model_override = str(defaults.get("model_override") or "").strip()
    if model_override:
        settings.model = model_override
    preset = get_review_preset(conversation.get("preset_key"))
    base_run = run_store.get_run(base["run_id"]) if base.get("run_id") else None
    diagnostics = _load_json_if_exists(str((base_run or {}).get("result", {}).get("diagnostics_path", "")))
    summary = _load_json_if_exists(str((base_run or {}).get("result", {}).get("summary_path", "")))
    doc_outline = _summarize_document(base["path"])
    diagnostics_summary = ""
    if diagnostics and isinstance(diagnostics.get("overview"), dict):
        overview = diagnostics["overview"]
        diagnostics_summary = str(overview.get("summary") or "").strip()
    summary_text = ""
    if summary:
        summary_text = json.dumps(summary, ensure_ascii=False)[:1800]

    system_prompt = (
        "You are an academic manuscript assistant. "
        "Answer in Chinese. Be specific, concise, and action-oriented. "
        "If the user asks for modifications, explain what should change and why, but do not claim the document is already edited "
        "unless this is an apply-edit turn. "
        "When evidence is uncertain, say so."
    )
    agent = build_agent(settings, tools=[], system_prompt=system_prompt)
    payload = {
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Preset: {preset.label}\n"
                    f"Preset guidance: {preset.system_prompt_scaffold}\n"
                    f"Base source: {base['source']} ({base['label']})\n"
                    f"Document outline and excerpts:\n{doc_outline or 'No outline available.'}\n\n"
                    f"Latest diagnostics summary:\n{diagnostics_summary or 'None'}\n\n"
                    f"Latest revision summary JSON excerpt:\n{summary_text or 'None'}\n\n"
                    f"Recent conversation:\n{_recent_messages_text(conversation.get('messages', [])) or 'None'}\n\n"
                    f"User request:\n{prompt.strip()}"
                ),
            }
        ]
    }
    result = agent.invoke(payload, config={"configurable": {"thread_id": f"{conversation['thread_id']}:chat"}})
    content = _message_text(result)
    if not content:
        raise RuntimeError("The model returned an empty response")
    return content


def create_conversation_chat_message(
    conversation_store: ReviewConversationStore,
    run_store: RunStore,
    *,
    conversation_id: str,
    content: str,
    base_source: str,
    base_run_id: str,
) -> dict[str, Any]:
    text = (content or "").strip()
    if not text:
        raise ValueError("Message content is required")
    base = resolve_conversation_base(
        conversation_store,
        run_store,
        conversation_id,
        base_source=base_source,
        base_run_id=base_run_id,
    )
    user_message = conversation_store.append_message(
        conversation_id,
        role="user",
        mode="chat",
        content=text,
        status="completed",
        base_source=base["source"],
        base_run_id=base["run_id"],
    )
    conversation = conversation_store.get_internal_conversation(conversation_id)
    if conversation is None:
        raise KeyError(conversation_id)
    reply = generate_conversation_reply(conversation, base=base, prompt=text, run_store=run_store)
    assistant_message = conversation_store.append_message(
        conversation_id,
        role="assistant",
        mode="chat",
        content=reply,
        status="completed",
        base_source=base["source"],
        base_run_id=base["run_id"],
    )
    return {"user_message": user_message, "assistant_message": assistant_message, "linked_run": None}


def _merge_apply_options(conversation: dict, options_patch: dict[str, Any] | None) -> dict[str, Any]:
    merged = deepcopy(conversation.get("defaults", {}))
    merged.update(normalize_review_options(options_patch))
    merged["diagnostics"] = bool(merged.get("diagnostics", True))
    merged["diagnostics_only"] = False
    merged["preset_key"] = conversation.get("preset_key") or merged.get("preset_key") or "general_academic"
    return merged


def _base_label(base: dict[str, Any]) -> str:
    if base["source"] == "original":
        return "原稿"
    return base["label"]


def create_conversation_apply_message(
    conversation_store: ReviewConversationStore,
    run_store: RunStore,
    *,
    root_dir: str,
    conversation_id: str,
    content: str,
    base_source: str,
    base_run_id: str,
    options_patch: dict[str, Any] | None,
) -> dict[str, Any]:
    text = (content or "").strip()
    if not text:
        raise ValueError("Message content is required")
    conversation = conversation_store.get_internal_conversation(conversation_id)
    if conversation is None:
        raise KeyError(conversation_id)
    active_run_id = (conversation.get("active_run_id") or "").strip()
    if active_run_id:
        active_run = run_store.get_run(active_run_id)
        if active_run and active_run.get("status") in {"created", "queued", "running"}:
            raise RuntimeError("This conversation already has an active revision run")

    base = resolve_conversation_base(
        conversation_store,
        run_store,
        conversation_id,
        base_source=base_source,
        base_run_id=base_run_id,
    )
    merged_options = _merge_apply_options(conversation, options_patch)
    next_version = int(conversation.get("head_version_no") or 0) + 1
    user_message = conversation_store.append_message(
        conversation_id,
        role="user",
        mode="apply",
        content=text,
        status="submitted",
        base_source=base["source"],
        base_run_id=base["run_id"],
    )
    assistant_message = conversation_store.append_message(
        conversation_id,
        role="assistant",
        mode="apply",
        content=f"正在基于{_base_label(base)}应用修改，完成后会生成 V{next_version}。",
        status="running",
        base_source=base["source"],
        base_run_id=base["run_id"],
        metadata={"planned_version_no": next_version},
    )
    conversation_store.set_active_run(conversation_id, f"pending:{assistant_message['id']}")

    request = ReviewRequest(
        filename=base["filename"],
        file_bytes=base["path"].read_bytes(),
        intent=text,
        expert_view=str(merged_options.get("expert_view") or ""),
        constraints=list(merged_options.get("constraints") or []),
        preset_key=str(merged_options.get("preset_key") or conversation.get("preset_key") or "general_academic"),
        revision_engine=str(merged_options.get("revision_engine") or "auto"),
        format_profile=str(merged_options.get("format_profile") or "none"),
        auto_approve=bool(merged_options.get("auto_approve", True)),
        allow_python_docx_fallback=bool(merged_options.get("allow_python_docx_fallback", False)),
        comment_author=str(merged_options.get("comment_author") or "Reviewer"),
        strip_existing_comments=bool(merged_options.get("strip_existing_comments", False)),
        prefer_replace=bool(merged_options.get("prefer_replace", False)),
        allow_expansion=bool(merged_options.get("allow_expansion", False)),
        expansion_level=str(merged_options.get("expansion_level") or "none"),
        allow_web_search=bool(merged_options.get("allow_web_search", False)),
        focus_only=bool(merged_options.get("focus_only", False)),
        memory_scope="session",
        inline_context=str(merged_options.get("inline_context") or "boundary"),
        chunk_context=int(merged_options.get("chunk_context", 2)),
        context_max_chars=int(merged_options.get("context_max_chars", 1200)),
        extract_docx_images=bool(merged_options.get("extract_docx_images", False)),
        extract_tables=bool(merged_options.get("extract_tables", False)),
        table_image_understanding=bool(merged_options.get("table_image_understanding", False)),
        table_image_prompt=str(merged_options.get("table_image_prompt") or "Describe the figure for academic review."),
        parallel_review=bool(merged_options.get("parallel_review", True)),
        parallel_workers=int(merged_options.get("parallel_workers", 4)),
        chunk_size=int(merged_options.get("chunk_size", 40)),
        parallel_min_paragraphs=int(merged_options.get("parallel_min_paragraphs", 80)),
        model_override=str(merged_options.get("model_override") or ""),
        diagnostics=bool(merged_options.get("diagnostics", True)),
        diagnostics_only=False,
        conversation_id=conversation_id,
        base_run_id=str(base["run_id"] or ""),
        version_no=next_version,
        source_artifact=str(base["artifact_name"] or ""),
        thread_id_override=str(conversation.get("thread_id") or ""),
    )

    def _on_complete(run: dict) -> None:
        label = f"V{next_version}"
        conversation_store.add_version(
            conversation_id,
            run_id=run["id"],
            base_run_id=str(base["run_id"] or ""),
            artifact_name="revised_docx",
            label=label,
            source_artifact=str(base["artifact_name"] or ""),
        )
        model_output = str((run.get("result") or {}).get("model_output") or "").strip()
        summary = f"已完成 {label}，基于{_base_label(base)}生成新修订版。"
        if model_output:
            summary = f"{summary}\n\n{model_output[:1200]}"
        conversation_store.update_message(
            conversation_id,
            assistant_message["id"],
            status="completed",
            content=summary,
            linked_run_id=run["id"],
        )

    def _on_failed(run: dict) -> None:
        conversation_store.clear_active_run(conversation_id)
        error = str(run.get("error") or "Revision failed").strip()
        conversation_store.update_message(
            conversation_id,
            assistant_message["id"],
            status="failed",
            content=f"本轮修改失败：{error}",
            linked_run_id=run.get("id", ""),
        )

    try:
        linked_run = create_review_run(
            run_store,
            request,
            root_dir=root_dir,
            on_complete=_on_complete,
            on_failed=_on_failed,
        )
    except Exception:
        conversation_store.update_message(
            conversation_id,
            assistant_message["id"],
            status="failed",
            content="本轮修改创建失败，请检查参数或运行环境。",
        )
        conversation_store.clear_active_run(conversation_id)
        raise

    current = conversation_store.get_internal_conversation(conversation_id)
    if current is not None and str(current.get("active_run_id") or "").startswith("pending:"):
        conversation_store.set_active_run(conversation_id, linked_run["id"])
    assistant_message = conversation_store.update_message(
        conversation_id,
        assistant_message["id"],
        linked_run_id=linked_run["id"],
        metadata={"planned_version_no": next_version, "run_id": linked_run["id"]},
    ) or assistant_message
    return {"user_message": user_message, "assistant_message": assistant_message, "linked_run": linked_run}
