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


def test_review_conversation_endpoints_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ROOT_DIR", str(tmp_path))
    client = TestClient(create_app())

    create_response = client.post(
        "/api/review/conversations",
        files={"file": ("demo.docx", b"docx-content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"title": "demo", "preset_key": "general_academic"},
    )
    assert create_response.status_code == 200
    payload = create_response.json()
    conversation_id = payload["id"]
    assert payload["title"] == "demo"
    assert payload["original_artifact"]["download_url"].endswith("/original_docx")

    list_response = client.get("/api/review/conversations")
    assert list_response.status_code == 200
    assert any(item["id"] == conversation_id for item in list_response.json()["conversations"])

    detail_response = client.get(f"/api/review/conversations/{conversation_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == conversation_id


def test_review_conversation_pending_active_run_is_not_exposed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ROOT_DIR", str(tmp_path))
    client = TestClient(create_app())
    conversation_store = client.app.state.review_conversation_store
    conversation = conversation_store.create_conversation(
        title="demo",
        input_filename="demo.docx",
        preset_key="general_academic",
        defaults={"revision_engine": "auto"},
        original_filename="demo.docx",
        original_bytes=b"docx-content",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    conversation_store.set_active_run(conversation["id"], "pending:assistant-message")

    detail_response = client.get(f"/api/review/conversations/{conversation['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["active_run_id"] == ""

    list_response = client.get("/api/review/conversations")
    assert list_response.status_code == 200
    item = next(item for item in list_response.json()["conversations"] if item["id"] == conversation["id"])
    assert item["active_run_id"] == ""


def test_review_conversation_message_endpoints_accept_chat_and_apply(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENT_ROOT_DIR", str(tmp_path))
    client = TestClient(create_app())
    conversation_store = client.app.state.review_conversation_store
    conversation = conversation_store.create_conversation(
        title="demo",
        input_filename="demo.docx",
        preset_key="general_academic",
        defaults={"revision_engine": "auto"},
        original_filename="demo.docx",
        original_bytes=b"docx-content",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    monkeypatch.setattr(
        "app.api.routes_review.create_conversation_chat_message",
        lambda *_args, **_kwargs: {
            "user_message": {
                "id": "user-chat",
                "role": "user",
                "mode": "chat",
                "content": "摘要有哪些问题",
                "status": "completed",
                "base_source": "latest",
                "base_run_id": "",
                "linked_run_id": "",
                "metadata": {},
                "created_at": "2026-03-22 00:00:00",
                "updated_at": "2026-03-22 00:00:00",
            },
            "assistant_message": {
                "id": "assistant-chat",
                "role": "assistant",
                "mode": "chat",
                "content": "摘要偏长。",
                "status": "completed",
                "base_source": "latest",
                "base_run_id": "",
                "linked_run_id": "",
                "metadata": {},
                "created_at": "2026-03-22 00:00:00",
                "updated_at": "2026-03-22 00:00:00",
            },
            "linked_run": None,
        },
    )
    monkeypatch.setattr(
        "app.api.routes_review.create_conversation_apply_message",
        lambda *_args, **_kwargs: {
            "user_message": {
                "id": "user-apply",
                "role": "user",
                "mode": "apply",
                "content": "重写摘要",
                "status": "submitted",
                "base_source": "latest",
                "base_run_id": "",
                "linked_run_id": "",
                "metadata": {},
                "created_at": "2026-03-22 00:00:00",
                "updated_at": "2026-03-22 00:00:00",
            },
            "assistant_message": {
                "id": "assistant-apply",
                "role": "assistant",
                "mode": "apply",
                "content": "处理中",
                "status": "running",
                "base_source": "latest",
                "base_run_id": "",
                "linked_run_id": "run-apply",
                "metadata": {},
                "created_at": "2026-03-22 00:00:00",
                "updated_at": "2026-03-22 00:00:00",
            },
            "linked_run": {
                "id": "run-apply",
                "mode": "review",
                "title": "demo",
                "status": "running",
                "input_filename": "demo.docx",
                "params": {},
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
                "conversation_id": conversation["id"],
                "version_no": 1,
                "base_run_id": "",
                "source_artifact": "original_docx",
            },
        },
    )

    chat_response = client.post(
        f"/api/review/conversations/{conversation['id']}/messages",
        json={"mode": "chat", "content": "摘要有哪些问题", "base_source": "latest"},
    )
    assert chat_response.status_code == 200
    assert chat_response.json()["assistant_message"]["mode"] == "chat"

    apply_response = client.post(
        f"/api/review/conversations/{conversation['id']}/messages",
        json={"mode": "apply", "content": "重写摘要", "base_source": "latest", "options_patch": {"diagnostics": True}},
    )
    assert apply_response.status_code == 200
    assert apply_response.json()["linked_run"]["conversation_id"] == conversation["id"]


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
