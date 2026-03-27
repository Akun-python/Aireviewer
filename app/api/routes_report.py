from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from typing import List

from app.api.models import RunResponse
from app.services.report_service import (
    ReportCompleteRequest,
    ReportIntegrateRequest,
    ReportRequest,
    create_report_complete_run,
    create_report_integrate_run,
    create_report_run,
)
from app.services.run_store import RunStore


router = APIRouter(prefix="/api", tags=["report"])


def _serialize_run(run: dict) -> dict:
    payload = dict(run)
    artifacts = []
    for artifact in run.get("artifacts", []):
        item = dict(artifact)
        item["download_url"] = f"/api/runs/{run['id']}/artifacts/{item['name']}"
        artifacts.append(item)
    payload["artifacts"] = artifacts
    return payload


@router.post("/report/runs", response_model=RunResponse)
async def create_report_endpoint(
    request: Request,
    topic: str = Form(...),
    framework_text: str = Form(""),
    total_chars: int = Form(10000),
    allow_web_search: bool = Form(True),
    max_results_per_query: int = Form(5),
    section_timeout: int = Form(300),
    max_section_retries: int = Form(2),
    section_workers: int = Form(3),
    report_docx_engine: str = Form("auto"),
    format_profile: str = Form("thesis_standard"),
    toc_position: str = Form("before_outline"),
    model_override: str = Form(""),
):
    store: RunStore = request.app.state.run_store
    try:
        run = create_report_run(
            store,
            ReportRequest(
                topic=topic,
                framework_text=framework_text,
                total_chars=total_chars,
                allow_web_search=allow_web_search,
                max_results_per_query=max_results_per_query,
                section_timeout=section_timeout,
                max_section_retries=max_section_retries,
                section_workers=section_workers,
                report_docx_engine=report_docx_engine,
                format_profile=format_profile,
                toc_position=toc_position,
                model_override=model_override,
            ),
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_run(run)


@router.post("/report-complete/runs", response_model=RunResponse)
async def create_report_complete_endpoint(
    request: Request,
    file: UploadFile = File(...),
    topic: str = Form(""),
    allow_web_search: bool = Form(True),
    max_results_per_query: int = Form(5),
    section_timeout: int = Form(300),
    fill_empty_headings: bool = Form(True),
    format_profile: str = Form("thesis_standard"),
    toc_position: str = Form("before_outline"),
    model_override: str = Form(""),
):
    store: RunStore = request.app.state.run_store
    try:
        run = create_report_complete_run(
            store,
            ReportCompleteRequest(
                filename=file.filename or "report.docx",
                file_bytes=await file.read(),
                topic=topic,
                allow_web_search=allow_web_search,
                max_results_per_query=max_results_per_query,
                section_timeout=section_timeout,
                fill_empty_headings=fill_empty_headings,
                format_profile=format_profile,
                toc_position=toc_position,
                model_override=model_override,
            ),
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_run(run)


@router.post("/report-integrate/runs", response_model=RunResponse)
async def create_report_integrate_endpoint(
    request: Request,
    files: List[UploadFile] = File(...),
    topic: str = Form(""),
    toc_position: str = Form("after_title"),
    format_profile: str = Form("thesis_standard"),
    allow_llm: bool = Form(True),
    auto_captions: bool = Form(True),
    fixed_order_text: str = Form(""),
    model_override: str = Form(""),
):
    store: RunStore = request.app.state.run_store
    fixed_order = [line.strip() for line in fixed_order_text.splitlines() if line.strip()]
    try:
        run = create_report_integrate_run(
            store,
            ReportIntegrateRequest(
                chapter_files=[(file.filename or f"chapter_{idx}.docx", await file.read()) for idx, file in enumerate(files, start=1)],
                topic=topic,
                toc_position=toc_position,
                format_profile=format_profile,
                allow_llm=allow_llm,
                auto_captions=auto_captions,
                fixed_order=fixed_order,
                model_override=model_override,
            ),
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_run(run)
