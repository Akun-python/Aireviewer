from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse

from app.api.models import HealthResponse, RunListResponse
from app.services.capability_service import get_capabilities
from app.services.run_store import RunStore


router = APIRouter(tags=["system"])


def _serialize_run(run: dict) -> dict:
    payload = dict(run)
    artifacts = []
    for artifact in run.get("artifacts", []):
        item = dict(artifact)
        item["download_url"] = f"/api/runs/{run['id']}/artifacts/{item['name']}"
        artifacts.append(item)
    payload["artifacts"] = artifacts
    return payload


@router.get("/api/health", response_model=HealthResponse)
async def get_health():
    return {"status": "ok"}


@router.get("/api/capabilities")
async def get_capabilities_endpoint(request: Request):
    return get_capabilities(request.app.state.root_dir)


@router.get("/api/runs", response_model=RunListResponse)
async def list_runs(request: Request, mode: str | None = Query(default=None)):
    store: RunStore = request.app.state.run_store
    runs = [_serialize_run(item) for item in store.list_runs(mode=mode)]
    return {"runs": runs}


@router.get("/api/runs/{run_id}")
async def get_run(request: Request, run_id: str):
    store: RunStore = request.app.state.run_store
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _serialize_run(run)


def _format_sse(event: dict) -> str:
    return (
        f"id: {event['id']}\n"
        f"event: {event['type']}\n"
        f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    )


@router.get("/api/runs/{run_id}/events")
async def stream_run_events(request: Request, run_id: str, after: int = 0):
    store: RunStore = request.app.state.run_store
    run = store.get_run(run_id)
    if run is None:
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


@router.get("/api/runs/{run_id}/artifacts")
async def list_run_artifacts(request: Request, run_id: str):
    store: RunStore = request.app.state.run_store
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"artifacts": _serialize_run(run).get("artifacts", [])}


@router.get("/api/runs/{run_id}/artifacts/{artifact_name}")
async def download_artifact(request: Request, run_id: str, artifact_name: str):
    store: RunStore = request.app.state.run_store
    artifact = store.get_artifact(run_id, artifact_name)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    path = Path(artifact["path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file is missing")
    return FileResponse(path=path, filename=artifact["filename"], media_type=artifact["content_type"])
