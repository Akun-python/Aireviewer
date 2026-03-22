from __future__ import annotations

import os
from pathlib import Path

import uvicorn


if __name__ == "__main__":
    os.environ.setdefault("AGENT_ROOT_DIR", str(Path(__file__).resolve().parent))
    host = os.getenv("REVIEWER_API_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.getenv("REVIEWER_API_PORT", "8011"))
    reload_enabled = os.getenv("REVIEWER_API_RELOAD", "").strip().lower() in {"1", "true", "yes", "y", "on"}
    uvicorn.run("app.api.main:app", host=host, port=port, reload=reload_enabled)
