from __future__ import annotations

from pathlib import Path

from app.services.review_conversation_service import create_review_conversation, resolve_conversation_base
from app.services.review_conversation_store import ReviewConversationStore
from app.services.run_store import RunStore


def test_review_conversation_store_tracks_messages_and_versions(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ROOT_DIR", str(tmp_path))
    store = ReviewConversationStore(str(tmp_path))

    conversation = store.create_conversation(
        title="demo",
        input_filename="demo.docx",
        preset_key="general_academic",
        defaults={"revision_engine": "auto"},
        original_filename="demo.docx",
        original_bytes=b"docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        assistant_message="ready",
    )
    conversation_id = conversation["id"]

    user_message = store.append_message(
        conversation_id,
        role="user",
        mode="chat",
        content="hello",
        status="completed",
    )
    assistant_message = store.update_message(conversation_id, user_message["id"], content="hello updated")
    assert assistant_message is not None

    store.set_active_run(conversation_id, "run-1")
    version = store.add_version(
        conversation_id,
        run_id="run-1",
        base_run_id="",
        artifact_name="revised_docx",
        label="V1",
        source_artifact="original_docx",
    )

    loaded = store.get_conversation(conversation_id)
    assert loaded is not None
    assert loaded["head_run_id"] == "run-1"
    assert loaded["head_version_no"] == 1
    assert loaded["active_run_id"] == ""
    assert version["version_no"] == 1
    assert len(loaded["messages"]) == 2


def test_resolve_conversation_base_handles_original_latest_and_run(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ROOT_DIR", str(tmp_path))
    conversation_store = ReviewConversationStore(str(tmp_path))
    run_store = RunStore(str(tmp_path))

    conversation = create_review_conversation(
        conversation_store,
        filename="demo.docx",
        file_bytes=b"docx-content",
        title="demo",
        preset_key="general_academic",
        defaults={"revision_engine": "auto"},
    )
    conversation_id = conversation["id"]

    original = resolve_conversation_base(conversation_store, run_store, conversation_id, base_source="latest")
    assert original["source"] == "original"
    assert original["filename"] == "demo.docx"

    run = run_store.create_run(
        mode="review",
        input_filename="demo.docx",
        params={"intent": "revise"},
        title="demo",
        extra={"conversation_id": conversation_id, "version_no": 1},
    )
    revised_path = Path(run["run_dir"]) / "demo_v1.docx"
    revised_path.write_bytes(b"v1")
    run_store.add_artifact(
        run["id"],
        name="revised_docx",
        label="revised",
        path=revised_path,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    conversation_store.add_version(
        conversation_id,
        run_id=run["id"],
        base_run_id="",
        artifact_name="revised_docx",
        label="V1",
        source_artifact="original_docx",
    )

    latest = resolve_conversation_base(conversation_store, run_store, conversation_id, base_source="latest")
    assert latest["source"] == "latest"
    assert latest["run_id"] == run["id"]

    explicit = resolve_conversation_base(conversation_store, run_store, conversation_id, base_source="run", base_run_id=run["id"])
    assert explicit["source"] == "run"
    assert explicit["path"] == revised_path
