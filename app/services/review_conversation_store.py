from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
import os
from pathlib import Path
import threading
import time
import uuid

from app.tools.path_utils import ensure_workspace_dir


def _now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def _artifact_size(path: Path) -> int:
    try:
        return int(path.stat().st_size)
    except Exception:
        return 0


class ReviewConversationStore:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()
        self.base_dir = ensure_workspace_dir() / "review_conversations"
        self.conversations_dir = self.base_dir / "items"
        self.index_path = self.base_dir / "conversations.json"
        self.persist_error_path = self.base_dir / "persist_errors.log"
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conversations: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if not self.index_path.exists():
            return
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception:
            return
        conversations = payload.get("conversations", [])
        if not isinstance(conversations, list):
            return
        for item in conversations:
            if not isinstance(item, dict):
                continue
            conversation_id = item.get("id")
            if not isinstance(conversation_id, str) or not conversation_id:
                continue
            item["messages"] = [message for message in item.get("messages", []) if isinstance(message, dict)]
            item["versions"] = [version for version in item.get("versions", []) if isinstance(version, dict)]
            self._conversations[conversation_id] = item

    def _write_persist_error(self, message: str) -> None:
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            with self.persist_error_path.open("a", encoding="utf-8") as handle:
                handle.write(f"[{_now_iso()}] {message}\n")
        except Exception:
            return

    def _persist(self) -> None:
        serializable_conversations: list[dict] = [deepcopy(item) for item in self._conversations.values()]
        serializable_conversations.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        content = json.dumps({"conversations": serializable_conversations}, ensure_ascii=False, indent=2)
        last_error = ""
        for attempt in range(8):
            tmp_path = self.base_dir / f"conversations.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
            try:
                tmp_path.write_text(content, encoding="utf-8")
                os.replace(str(tmp_path), str(self.index_path))
                return
            except PermissionError as exc:
                last_error = str(exc)
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
                time.sleep(0.05 * (attempt + 1))
            except Exception as exc:
                last_error = str(exc)
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
                break

        fallback_path = self.base_dir / f"conversations.snapshot.{os.getpid()}.json"
        try:
            fallback_path.write_text(content, encoding="utf-8")
        except Exception as exc:
            detail = f"persist failed: {last_error or 'unknown'}; fallback snapshot failed: {exc}"
            self._write_persist_error(detail)
            return
        self._write_persist_error(
            f"persist failed: {last_error or 'unknown'}; wrote fallback snapshot to {fallback_path.name}"
        )

    def create_conversation(
        self,
        *,
        title: str,
        input_filename: str,
        preset_key: str,
        defaults: dict,
        original_filename: str,
        original_bytes: bytes,
        content_type: str,
        assistant_message: str = "",
    ) -> dict:
        with self._lock:
            conversation_id = uuid.uuid4().hex
            now = _now_iso()
            conversation_dir = self.conversations_dir / conversation_id
            conversation_dir.mkdir(parents=True, exist_ok=True)
            original_path = conversation_dir / original_filename
            original_path.write_bytes(original_bytes)
            record = {
                "id": conversation_id,
                "title": title,
                "input_filename": input_filename,
                "preset_key": preset_key,
                "defaults": deepcopy(defaults),
                "thread_id": f"review-conversation-{conversation_id}",
                "created_at": now,
                "updated_at": now,
                "head_run_id": "",
                "head_version_no": 0,
                "active_run_id": "",
                "conversation_dir": str(conversation_dir),
                "original_artifact": {
                    "name": "original_docx",
                    "label": "原始文稿",
                    "path": str(original_path),
                    "filename": original_path.name,
                    "size_bytes": _artifact_size(original_path),
                    "content_type": content_type,
                },
                "messages": [],
                "versions": [],
            }
            self._conversations[conversation_id] = record
            if assistant_message.strip():
                self._append_message_unlocked(
                    conversation_id,
                    role="assistant",
                    mode="chat",
                    content=assistant_message.strip(),
                    status="completed",
                )
            self._persist()
            return self._public_conversation(record)

    def list_conversations(self) -> list[dict]:
        with self._lock:
            items = [self._public_conversation(record) for record in self._conversations.values()]
            items.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
            return items

    def get_conversation(self, conversation_id: str) -> dict | None:
        with self._lock:
            record = self._conversations.get(conversation_id)
            if record is None:
                return None
            return self._public_conversation(record)

    def get_internal_conversation(self, conversation_id: str) -> dict | None:
        with self._lock:
            return self._conversations.get(conversation_id)

    def append_message(
        self,
        conversation_id: str,
        *,
        role: str,
        mode: str,
        content: str,
        status: str,
        base_source: str = "",
        base_run_id: str = "",
        linked_run_id: str = "",
        metadata: dict | None = None,
    ) -> dict:
        with self._lock:
            message = self._append_message_unlocked(
                conversation_id,
                role=role,
                mode=mode,
                content=content,
                status=status,
                base_source=base_source,
                base_run_id=base_run_id,
                linked_run_id=linked_run_id,
                metadata=metadata,
            )
            self._persist()
            return deepcopy(message)

    def _append_message_unlocked(
        self,
        conversation_id: str,
        *,
        role: str,
        mode: str,
        content: str,
        status: str,
        base_source: str = "",
        base_run_id: str = "",
        linked_run_id: str = "",
        metadata: dict | None = None,
    ) -> dict:
        record = self._conversations[conversation_id]
        now = _now_iso()
        message = {
            "id": uuid.uuid4().hex,
            "role": role,
            "mode": mode,
            "content": content,
            "status": status,
            "base_source": base_source,
            "base_run_id": base_run_id,
            "linked_run_id": linked_run_id,
            "metadata": deepcopy(metadata or {}),
            "created_at": now,
            "updated_at": now,
        }
        record.setdefault("messages", []).append(message)
        record["updated_at"] = now
        return message

    def update_message(self, conversation_id: str, message_id: str, **changes) -> dict | None:
        with self._lock:
            record = self._conversations.get(conversation_id)
            if record is None:
                return None
            messages = record.get("messages", [])
            for item in messages:
                if item.get("id") != message_id:
                    continue
                for key, value in changes.items():
                    if key in {"id", "role", "mode", "created_at"}:
                        continue
                    if key == "metadata" and isinstance(value, dict):
                        item["metadata"] = deepcopy(value)
                    else:
                        item[key] = value
                item["updated_at"] = _now_iso()
                record["updated_at"] = item["updated_at"]
                self._persist()
                return deepcopy(item)
            return None

    def set_active_run(self, conversation_id: str, run_id: str | None) -> None:
        with self._lock:
            record = self._conversations[conversation_id]
            record["active_run_id"] = (run_id or "").strip()
            record["updated_at"] = _now_iso()
            self._persist()

    def add_version(
        self,
        conversation_id: str,
        *,
        run_id: str,
        base_run_id: str,
        artifact_name: str,
        label: str,
        source_artifact: str,
    ) -> dict:
        with self._lock:
            record = self._conversations[conversation_id]
            next_version = int(record.get("head_version_no", 0)) + 1
            now = _now_iso()
            version = {
                "version_no": next_version,
                "run_id": run_id,
                "base_run_id": base_run_id,
                "artifact_name": artifact_name,
                "source_artifact": source_artifact,
                "label": label,
                "diagnostics_run_id": run_id,
                "created_at": now,
            }
            record.setdefault("versions", []).append(version)
            record["head_run_id"] = run_id
            record["head_version_no"] = next_version
            record["active_run_id"] = ""
            record["updated_at"] = now
            self._persist()
            return deepcopy(version)

    def clear_active_run(self, conversation_id: str) -> None:
        self.set_active_run(conversation_id, "")

    def _public_conversation(self, record: dict) -> dict:
        return deepcopy(record)


_STORES: dict[str, ReviewConversationStore] = {}
_STORE_LOCK = threading.Lock()


def get_review_conversation_store(root_dir: str) -> ReviewConversationStore:
    resolved_root = str(Path(root_dir).resolve())
    with _STORE_LOCK:
        store = _STORES.get(resolved_root)
        if store is None:
            store = ReviewConversationStore(resolved_root)
            _STORES[resolved_root] = store
        return store
