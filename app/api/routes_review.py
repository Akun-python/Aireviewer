from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.api.models import (
    ReviewConversationListResponse,
    ReviewConversationMessageActionResponse,
    ReviewConversationMessageRequest,
    ReviewConversationResponse,
    RunResponse,
)
from app.services.preset_service import list_review_presets
from app.services.review_conversation_service import (
    build_conversation_defaults,
    create_conversation_apply_message,
    create_conversation_chat_message,
    create_review_conversation,
)
from app.services.review_conversation_store import ReviewConversationStore
from app.services.review_service import ReviewRequest, create_review_run
from app.services.run_store import RunStore


router = APIRouter(prefix="/api/review", tags=["review"])


def _serialize_run(run: dict) -> dict:
    payload = dict(run)
    artifacts = []
    for artifact in run.get("artifacts", []):
        item = dict(artifact)
        item["download_url"] = f"/api/runs/{run['id']}/artifacts/{item['name']}"
        artifacts.append(item)
    payload["artifacts"] = artifacts
    return payload


def _parse_constraints(raw: str) -> list[str]:
    value = (raw or "").strip()
    if not value:
        return []
    try:
        data = json.loads(value)
    except Exception:
        return [line.strip() for line in value.splitlines() if line.strip()]
    if isinstance(data, list):
        return [str(item).strip() for item in data if str(item).strip()]
    return []


def _review_defaults_payload(
    *,
    expert_view: str,
    constraints_json: str,
    revision_engine: str,
    format_profile: str,
    auto_approve: bool,
    allow_python_docx_fallback: bool,
    comment_author: str,
    strip_existing_comments: bool,
    prefer_replace: bool,
    allow_expansion: bool,
    expansion_level: str,
    allow_web_search: bool,
    focus_only: bool,
    inline_context: str,
    chunk_context: int,
    context_max_chars: int,
    extract_docx_images: bool,
    extract_tables: bool,
    table_image_understanding: bool,
    table_image_prompt: str,
    parallel_review: bool,
    parallel_workers: int,
    chunk_size: int,
    parallel_min_paragraphs: int,
    model_override: str,
    diagnostics: bool,
) -> dict:
    return {
        "expert_view": expert_view,
        "constraints": _parse_constraints(constraints_json),
        "revision_engine": revision_engine,
        "format_profile": format_profile,
        "auto_approve": auto_approve,
        "allow_python_docx_fallback": allow_python_docx_fallback,
        "comment_author": comment_author,
        "strip_existing_comments": strip_existing_comments,
        "prefer_replace": prefer_replace,
        "allow_expansion": allow_expansion,
        "expansion_level": expansion_level,
        "allow_web_search": allow_web_search,
        "focus_only": focus_only,
        "inline_context": inline_context,
        "chunk_context": chunk_context,
        "context_max_chars": context_max_chars,
        "extract_docx_images": extract_docx_images,
        "extract_tables": extract_tables,
        "table_image_understanding": table_image_understanding,
        "table_image_prompt": table_image_prompt,
        "parallel_review": parallel_review,
        "parallel_workers": parallel_workers,
        "chunk_size": chunk_size,
        "parallel_min_paragraphs": parallel_min_paragraphs,
        "model_override": model_override,
        "diagnostics": diagnostics,
    }


def _serialize_conversation_summary(conversation: dict) -> dict:
    messages = [item for item in conversation.get("messages", []) if isinstance(item, dict)]
    last_message = messages[-1] if messages else {}
    last_excerpt = str(last_message.get("content") or "").strip().replace("\n", " ")
    active_run_id = str(conversation.get("active_run_id") or "").strip()
    public_active_run_id = "" if active_run_id.startswith("pending:") else active_run_id
    return {
        "id": conversation["id"],
        "title": conversation.get("title", ""),
        "input_filename": conversation.get("input_filename", ""),
        "preset_key": conversation.get("preset_key", ""),
        "created_at": conversation.get("created_at", ""),
        "updated_at": conversation.get("updated_at", ""),
        "head_run_id": conversation.get("head_run_id", ""),
        "head_version_no": int(conversation.get("head_version_no", 0) or 0),
        "active_run_id": public_active_run_id,
        "message_count": len(messages),
        "version_count": len([item for item in conversation.get("versions", []) if isinstance(item, dict)]),
        "last_message_excerpt": last_excerpt[:160],
    }


def _serialize_conversation(conversation: dict, run_store: RunStore) -> dict:
    payload = dict(conversation)
    active_run_id = str(payload.get("active_run_id") or "").strip()
    if active_run_id.startswith("pending:"):
        payload["active_run_id"] = ""
    original_artifact = dict(payload.get("original_artifact", {}))
    if original_artifact:
        original_artifact["download_url"] = f"/api/review/conversations/{conversation['id']}/artifacts/{original_artifact['name']}"
        payload["original_artifact"] = original_artifact
    versions = []
    for version in payload.get("versions", []):
        if not isinstance(version, dict):
            continue
        item = dict(version)
        item["download_url"] = f"/api/runs/{item['run_id']}/artifacts/{item['artifact_name']}"
        versions.append(item)
    payload["versions"] = versions
    head_run_id = str(payload.get("head_run_id") or "").strip()
    payload["head_run"] = _serialize_run(run_store.get_run(head_run_id)) if head_run_id and run_store.get_run(head_run_id) else None
    return payload


@router.post("/runs", response_model=RunResponse)
async def create_review_run_endpoint(
    request: Request,
    file: UploadFile = File(...),
    intent: str = Form(""),
    expert_view: str = Form("Document reviewer"),
    constraints_json: str = Form("[]"),
    preset_key: str = Form("general_academic"),
    revision_engine: str = Form("auto"),
    format_profile: str = Form("none"),
    auto_approve: bool = Form(True),
    allow_python_docx_fallback: bool = Form(False),
    comment_author: str = Form("Reviewer"),
    strip_existing_comments: bool = Form(False),
    prefer_replace: bool = Form(False),
    allow_expansion: bool = Form(False),
    expansion_level: str = Form("none"),
    allow_web_search: bool = Form(False),
    focus_only: bool = Form(False),
    memory_scope: str = Form("document"),
    inline_context: str = Form("boundary"),
    chunk_context: int = Form(2),
    context_max_chars: int = Form(1200),
    extract_docx_images: bool = Form(False),
    extract_tables: bool = Form(False),
    table_image_understanding: bool = Form(False),
    table_image_prompt: str = Form("Describe the figure for academic review."),
    parallel_review: bool = Form(True),
    parallel_workers: int = Form(4),
    chunk_size: int = Form(40),
    parallel_min_paragraphs: int = Form(80),
    model_override: str = Form(""),
    diagnostics: bool = Form(True),
    diagnostics_only: bool = Form(False),
):
    store: RunStore = request.app.state.run_store
    root_dir: str = request.app.state.root_dir
    try:
        payload = ReviewRequest(
            filename=file.filename or "document.docx",
            file_bytes=await file.read(),
            intent=intent,
            expert_view=expert_view,
            constraints=_parse_constraints(constraints_json),
            preset_key=preset_key,
            revision_engine=revision_engine,
            format_profile=format_profile,
            auto_approve=auto_approve,
            allow_python_docx_fallback=allow_python_docx_fallback,
            comment_author=comment_author,
            strip_existing_comments=strip_existing_comments,
            prefer_replace=prefer_replace,
            allow_expansion=allow_expansion,
            expansion_level=expansion_level,
            allow_web_search=allow_web_search,
            focus_only=focus_only,
            memory_scope=memory_scope,
            inline_context=inline_context,
            chunk_context=chunk_context,
            context_max_chars=context_max_chars,
            extract_docx_images=extract_docx_images,
            extract_tables=extract_tables,
            table_image_understanding=table_image_understanding,
            table_image_prompt=table_image_prompt,
            parallel_review=parallel_review,
            parallel_workers=parallel_workers,
            chunk_size=chunk_size,
            parallel_min_paragraphs=parallel_min_paragraphs,
            model_override=model_override,
            diagnostics=diagnostics,
            diagnostics_only=diagnostics_only,
        )
        run = create_review_run(store, payload, root_dir=root_dir)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_run(run)


@router.post("/conversations", response_model=ReviewConversationResponse)
async def create_review_conversation_endpoint(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(""),
    preset_key: str = Form("general_academic"),
    expert_view: str = Form("Document reviewer"),
    constraints_json: str = Form("[]"),
    revision_engine: str = Form("auto"),
    format_profile: str = Form("none"),
    auto_approve: bool = Form(True),
    allow_python_docx_fallback: bool = Form(False),
    comment_author: str = Form("Reviewer"),
    strip_existing_comments: bool = Form(False),
    prefer_replace: bool = Form(False),
    allow_expansion: bool = Form(False),
    expansion_level: str = Form("none"),
    allow_web_search: bool = Form(False),
    focus_only: bool = Form(False),
    inline_context: str = Form("boundary"),
    chunk_context: int = Form(2),
    context_max_chars: int = Form(1200),
    extract_docx_images: bool = Form(False),
    extract_tables: bool = Form(False),
    table_image_understanding: bool = Form(False),
    table_image_prompt: str = Form("Describe the figure for academic review."),
    parallel_review: bool = Form(True),
    parallel_workers: int = Form(4),
    chunk_size: int = Form(40),
    parallel_min_paragraphs: int = Form(80),
    model_override: str = Form(""),
    diagnostics: bool = Form(True),
):
    conversation_store: ReviewConversationStore = request.app.state.review_conversation_store
    run_store: RunStore = request.app.state.run_store
    defaults = build_conversation_defaults(
        _review_defaults_payload(
            expert_view=expert_view,
            constraints_json=constraints_json,
            revision_engine=revision_engine,
            format_profile=format_profile,
            auto_approve=auto_approve,
            allow_python_docx_fallback=allow_python_docx_fallback,
            comment_author=comment_author,
            strip_existing_comments=strip_existing_comments,
            prefer_replace=prefer_replace,
            allow_expansion=allow_expansion,
            expansion_level=expansion_level,
            allow_web_search=allow_web_search,
            focus_only=focus_only,
            inline_context=inline_context,
            chunk_context=chunk_context,
            context_max_chars=context_max_chars,
            extract_docx_images=extract_docx_images,
            extract_tables=extract_tables,
            table_image_understanding=table_image_understanding,
            table_image_prompt=table_image_prompt,
            parallel_review=parallel_review,
            parallel_workers=parallel_workers,
            chunk_size=chunk_size,
            parallel_min_paragraphs=parallel_min_paragraphs,
            model_override=model_override,
            diagnostics=diagnostics,
        ),
        preset_key=preset_key,
    )
    try:
        conversation = create_review_conversation(
            conversation_store,
            filename=file.filename or "document.docx",
            file_bytes=await file.read(),
            title=title,
            preset_key=preset_key,
            defaults=defaults,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_conversation(conversation, run_store)


@router.get("/conversations", response_model=ReviewConversationListResponse)
async def list_review_conversations(request: Request):
    conversation_store: ReviewConversationStore = request.app.state.review_conversation_store
    items = [_serialize_conversation_summary(item) for item in conversation_store.list_conversations()]
    return {"conversations": items}


@router.get("/conversations/{conversation_id}", response_model=ReviewConversationResponse)
async def get_review_conversation(conversation_id: str, request: Request):
    conversation_store: ReviewConversationStore = request.app.state.review_conversation_store
    run_store: RunStore = request.app.state.run_store
    conversation = conversation_store.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _serialize_conversation(conversation, run_store)


@router.post("/conversations/{conversation_id}/messages", response_model=ReviewConversationMessageActionResponse)
async def create_review_conversation_message(
    conversation_id: str,
    payload: ReviewConversationMessageRequest,
    request: Request,
):
    conversation_store: ReviewConversationStore = request.app.state.review_conversation_store
    run_store: RunStore = request.app.state.run_store
    root_dir: str = request.app.state.root_dir
    try:
        mode = (payload.mode or "").strip().lower()
        if mode == "chat":
            response = create_conversation_chat_message(
                conversation_store,
                run_store,
                conversation_id=conversation_id,
                content=payload.content,
                base_source=payload.base_source,
                base_run_id=payload.base_run_id,
            )
        elif mode == "apply":
            response = create_conversation_apply_message(
                conversation_store,
                run_store,
                root_dir=root_dir,
                conversation_id=conversation_id,
                content=payload.content,
                base_source=payload.base_source,
                base_run_id=payload.base_run_id,
                options_patch=payload.options_patch,
            )
        else:
            raise ValueError("mode must be chat or apply")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc
    except RuntimeError as exc:
        detail = str(exc)
        status_code = 409 if "active revision run" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    serialized = dict(response)
    linked_run = serialized.get("linked_run")
    if isinstance(linked_run, dict):
        serialized["linked_run"] = _serialize_run(linked_run)
    return serialized


@router.get("/conversations/{conversation_id}/artifacts/{artifact_name}")
async def download_review_conversation_artifact(conversation_id: str, artifact_name: str, request: Request):
    conversation_store: ReviewConversationStore = request.app.state.review_conversation_store
    conversation = conversation_store.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    original_artifact = conversation.get("original_artifact", {})
    if artifact_name != original_artifact.get("name"):
        raise HTTPException(status_code=404, detail="Artifact not found")
    path = Path(original_artifact["path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file is missing")
    return FileResponse(path=path, filename=original_artifact["filename"], media_type=original_artifact["content_type"])


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_review_run(run_id: str, request: Request):
    store: RunStore = request.app.state.run_store
    run = store.get_run(run_id)
    if run is None or run.get("mode") != "review":
        raise HTTPException(status_code=404, detail="Run not found")
    return _serialize_run(run)


@router.get("/presets")
async def get_review_presets():
    return {"presets": list_review_presets()}


@router.get("/runs/{run_id}/diagnostics")
async def get_review_run_diagnostics(run_id: str, request: Request):
    store: RunStore = request.app.state.run_store
    run = store.get_run(run_id)
    if run is None or run.get("mode") != "review":
        raise HTTPException(status_code=404, detail="Run not found")
    diagnostics_artifact = next(
        (
            artifact
            for artifact in run.get("artifacts", [])
            if isinstance(artifact, dict) and artifact.get("name") == "diagnostics_json"
        ),
        None,
    )
    if not diagnostics_artifact:
        raise HTTPException(status_code=404, detail="Diagnostics artifact not found")
    diagnostics_path = Path(diagnostics_artifact["path"])
    if not diagnostics_path.exists():
        raise HTTPException(status_code=404, detail="Diagnostics file is missing")
    try:
        return json.loads(diagnostics_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to read diagnostics: {exc}") from exc


def _format_sse(event: dict) -> str:
    return (
        f"id: {event['id']}\n"
        f"event: {event['type']}\n"
        f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    )


@router.get("/runs/{run_id}/events")
async def stream_review_run_events(run_id: str, request: Request, after: int = 0):
    store: RunStore = request.app.state.run_store
    run = store.get_run(run_id)
    if run is None or run.get("mode") != "review":
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():
        last_id = int(after)
        while True:
            if await request.is_disconnected():
                break
            events = await asyncio.to_thread(store.wait_for_events, run_id, after_id=last_id, timeout_s=10.0)
            if not events:
                current = store.get_run(run_id)
                if current and current.get("status") in {"completed", "failed"} and int(current.get("event_count", 0)) <= last_id:
                    break
                yield ": keep-alive\n\n"
                continue
            for event in events:
                last_id = int(event.get("id", last_id))
                yield _format_sse(event)
            current = store.get_run(run_id)
            if current and current.get("status") in {"completed", "failed"} and int(current.get("event_count", 0)) <= last_id:
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")
