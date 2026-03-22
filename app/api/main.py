from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_report import router as report_router
from app.api.routes_review import router as review_router
from app.api.routes_runs import router as system_router
from app.services.run_store import get_run_store
from app.settings import load_settings


def create_app() -> FastAPI:
    settings = load_settings()
    root_dir = str(Path(settings.root_dir).resolve())
    app = FastAPI(title="Reviewer API", version="0.1.0")

    cors_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:4174",
        "http://127.0.0.1:4174",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ]
    extra_origins = [item.strip() for item in os.getenv("REVIEWER_CORS_ORIGINS", "").split(",") if item.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins + extra_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.root_dir = root_dir
    app.state.run_store = get_run_store(root_dir)

    @app.get("/")
    async def root():
        return {"name": "Reviewer API", "version": "0.1.0"}

    app.include_router(system_router)
    app.include_router(review_router)
    app.include_router(report_router)
    return app


app = create_app()
