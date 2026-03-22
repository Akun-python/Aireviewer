from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import create_app


def test_api_health_and_capabilities() -> None:
    client = TestClient(create_app())

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    capabilities = client.get("/api/capabilities")
    assert capabilities.status_code == 200
    payload = capabilities.json()
    assert "features" in payload
    assert "review" in payload
    assert "engines" in payload["review"]


def test_api_runs_endpoint_returns_list() -> None:
    client = TestClient(create_app())
    response = client.get("/api/runs?mode=review")
    assert response.status_code == 200
    assert isinstance(response.json()["runs"], list)


def test_review_presets_endpoint_returns_presets() -> None:
    client = TestClient(create_app())
    response = client.get("/api/review/presets")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["presets"], list)
    assert any(item["key"] == "general_academic" for item in payload["presets"])


def test_generic_run_endpoint_returns_serialized_run(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ROOT_DIR", str(tmp_path))
    client = TestClient(create_app())
    store = client.app.state.run_store
    run = store.create_run(mode="review", input_filename="demo.docx", params={"intent": "check"}, title="demo")

    response = client.get(f"/api/runs/{run['id']}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == run["id"]
    assert payload["mode"] == "review"


def test_review_diagnostics_endpoint_reads_json_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ROOT_DIR", str(tmp_path))
    client = TestClient(create_app())
    store = client.app.state.run_store
    run = store.create_run(mode="review", input_filename="demo.docx", params={"intent": "check"}, title="demo")
    diagnostics_path = Path(run["run_dir"]) / "demo.diagnostics.json"
    payload = {"overview": {"average_score": 88.5}, "pre_review": {}, "post_review": {}, "change_risk": {}}
    diagnostics_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    store.add_artifact(
        run["id"],
        name="diagnostics_json",
        label="diagnostics",
        path=diagnostics_path,
        content_type="application/json",
    )

    response = client.get(f"/api/review/runs/{run['id']}/diagnostics")
    assert response.status_code == 200
    assert response.json()["overview"]["average_score"] == 88.5


def test_review_create_endpoint_accepts_preset_and_diagnostics(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENT_ROOT_DIR", str(tmp_path))
    captured: dict[str, object] = {}

    def fake_create_review_run(store, request, *, root_dir: str) -> dict:
        captured["request"] = request
        captured["root_dir"] = root_dir
        return {
            "id": "run-review",
            "mode": "review",
            "title": "demo",
            "status": "created",
            "input_filename": request.filename,
            "params": request.to_store_params(),
            "created_at": "2026-03-22 00:00:00",
            "updated_at": "2026-03-22 00:00:00",
            "started_at": "",
            "finished_at": "",
            "error": "",
            "run_dir": str(tmp_path),
            "result": {},
            "artifacts": [],
            "event_count": 0,
            "events": [],
        }

    monkeypatch.setattr("app.api.routes_review.create_review_run", fake_create_review_run)
    client = TestClient(create_app())
    response = client.post(
        "/api/review/runs",
        files={"file": ("demo.docx", b"docx-content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={
            "intent": "检查章节结构",
            "preset_key": "social_science_fund",
            "diagnostics": "true",
            "diagnostics_only": "false",
            "constraints_json": json.dumps(["保持学术语气"], ensure_ascii=False),
        },
    )
    assert response.status_code == 200
    request_obj = captured["request"]
    assert getattr(request_obj, "preset_key") == "social_science_fund"
    assert getattr(request_obj, "diagnostics") is True
    assert getattr(request_obj, "constraints") == ["保持学术语气"]


def test_report_run_endpoints_accept_payloads(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENT_ROOT_DIR", str(tmp_path))
    calls: dict[str, object] = {}

    def _fake_run(mode: str, request_obj) -> dict:
        calls[mode] = request_obj
        return {
            "id": f"run-{mode}",
            "mode": mode,
            "title": mode,
            "status": "created",
            "input_filename": getattr(request_obj, "topic", "") or getattr(request_obj, "filename", "chapters"),
            "params": request_obj.to_store_params(),
            "created_at": "2026-03-22 00:00:00",
            "updated_at": "2026-03-22 00:00:00",
            "started_at": "",
            "finished_at": "",
            "error": "",
            "run_dir": str(tmp_path),
            "result": {},
            "artifacts": [],
            "event_count": 0,
            "events": [],
        }

    monkeypatch.setattr("app.api.routes_report.create_report_run", lambda store, request: _fake_run("report", request))
    monkeypatch.setattr(
        "app.api.routes_report.create_report_complete_run",
        lambda store, request: _fake_run("report-complete", request),
    )
    monkeypatch.setattr(
        "app.api.routes_report.create_report_integrate_run",
        lambda store, request: _fake_run("report-integrate", request),
    )

    client = TestClient(create_app())
    report_response = client.post("/api/report/runs", data={"topic": "乡村治理研究", "framework_text": "一、背景"})
    assert report_response.status_code == 200
    assert getattr(calls["report"], "topic") == "乡村治理研究"

    complete_response = client.post(
        "/api/report-complete/runs",
        files={"file": ("draft.docx", b"draft", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"topic": "乡村治理研究"},
    )
    assert complete_response.status_code == 200
    assert getattr(calls["report-complete"], "filename") == "draft.docx"

    integrate_response = client.post(
        "/api/report-integrate/runs",
        files=[
            ("files", ("chapter1.docx", b"chapter1", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ("files", ("chapter2.docx", b"chapter2", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ],
        data={"topic": "整合报告", "fixed_order_text": "chapter2.docx\nchapter1.docx"},
    )
    assert integrate_response.status_code == 200
    assert len(getattr(calls["report-integrate"], "chapter_files")) == 2
