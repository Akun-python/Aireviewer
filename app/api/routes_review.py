from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.api.models import RunResponse
from app.services.preset_service import list_review_presets
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


@router.post("/runs", response_model=RunResponse)
async def create_review_run_endpoint(
    request: Request,
    file: UploadFile = File(...),
    intent: str = Form(""),
    expert_view: str = Form("文档审阅员"),
    constraints_json: str = Form("[]"),
    preset_key: str = Form("general_academic"),
    revision_engine: str = Form("auto"),
    format_profile: str = Form("none"),
    auto_approve: bool = Form(True),
    allow_python_docx_fallback: bool = Form(False),
    comment_author: str = Form("呆塔大师兄"),
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
    table_image_prompt: str = Form("描述分析这张图"),
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
