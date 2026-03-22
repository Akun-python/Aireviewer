from __future__ import annotations

import os
from pathlib import Path

from app.services.run_store import RunStore


def test_run_store_tracks_events_and_artifacts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ROOT_DIR", str(tmp_path))
    store = RunStore(str(tmp_path))

    run = store.create_run(mode="review", input_filename="demo.docx", params={"intent": "test"}, title="demo")
    run_id = run["id"]

    store.update_status(run_id, status="running")
    store.append_event(run_id, event_type="run.log", message="hello")

    artifact_path = tmp_path / "artifact.txt"
    artifact_path.write_text("ok", encoding="utf-8")
    artifact = store.add_artifact(
        run_id,
        name="log_txt",
        label="运行日志",
        path=artifact_path,
        content_type="text/plain",
    )

    loaded = store.get_run(run_id)
    assert loaded is not None
    assert loaded["status"] == "running"
    assert loaded["event_count"] >= 2
    assert any(item["name"] == "log_txt" for item in loaded["artifacts"])
    assert artifact["filename"] == "artifact.txt"

    events_path = Path(loaded["run_dir"]) / "events.jsonl"
    assert events_path.exists()
    assert os.path.exists(artifact["path"])


def test_run_store_persist_fallback_does_not_raise(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ROOT_DIR", str(tmp_path))
    store = RunStore(str(tmp_path))

    run = store.create_run(mode="review", input_filename="demo.docx", params={"intent": "test"}, title="demo")
    run_id = run["id"]

    def always_fail_replace(src: str, dst: str) -> None:
        raise PermissionError("simulated replace failure")

    monkeypatch.setattr("app.services.run_store.os.replace", always_fail_replace)

    store.append_event(run_id, event_type="run.log", message="still running")

    fallback_snapshot = tmp_path / "workspace" / "api_runs" / f"runs.snapshot.{os.getpid()}.json"
    persist_log = tmp_path / "workspace" / "api_runs" / "persist_errors.log"
    assert fallback_snapshot.exists()
    assert persist_log.exists()
