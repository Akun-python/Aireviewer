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


class RunStore:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()
        self.base_dir = ensure_workspace_dir() / "api_runs"
        self.runs_dir = self.base_dir / "runs"
        self.index_path = self.base_dir / "runs.json"
        self.persist_error_path = self.base_dir / "persist_errors.log"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._runs: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if not self.index_path.exists():
            return
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception:
            return
        runs = payload.get("runs", [])
        if not isinstance(runs, list):
            return
        for item in runs:
            if not isinstance(item, dict):
                continue
            run_id = item.get("id")
            if not isinstance(run_id, str) or not run_id:
                continue
            item["events"] = []
            item["event_seq"] = 0
            self._runs[run_id] = item

    def _write_persist_error(self, message: str) -> None:
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            with self.persist_error_path.open("a", encoding="utf-8") as handle:
                handle.write(f"[{_now_iso()}] {message}\n")
        except Exception:
            return

    def _persist(self) -> None:
        serializable_runs: list[dict] = []
        for run in self._runs.values():
            payload = {key: value for key, value in run.items() if key not in {"events", "event_seq"}}
            serializable_runs.append(payload)
        serializable_runs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        content = json.dumps({"runs": serializable_runs}, ensure_ascii=False, indent=2)
        last_error = ""
        for attempt in range(8):
            tmp_path = self.base_dir / f"runs.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
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

        fallback_path = self.base_dir / f"runs.snapshot.{os.getpid()}.json"
        try:
            fallback_path.write_text(content, encoding="utf-8")
        except Exception as exc:
            detail = f"persist failed: {last_error or 'unknown'}; fallback snapshot failed: {exc}"
            self._write_persist_error(detail)
            return
        self._write_persist_error(
            f"persist failed: {last_error or 'unknown'}; wrote fallback snapshot to {fallback_path.name}"
        )

    def create_run(
        self,
        *,
        mode: str,
        input_filename: str,
        params: dict,
        title: str | None = None,
        extra: dict | None = None,
    ) -> dict:
        with self._lock:
            run_id = uuid.uuid4().hex
            now = _now_iso()
            run_dir = self.runs_dir / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            record = {
                "id": run_id,
                "mode": mode,
                "title": title or input_filename,
                "status": "created",
                "input_filename": input_filename,
                "params": deepcopy(params),
                "created_at": now,
                "updated_at": now,
                "started_at": "",
                "finished_at": "",
                "error": "",
                "run_dir": str(run_dir),
                "artifacts": {},
                "result": {},
                "events": [],
                "event_seq": 0,
            }
            if isinstance(extra, dict):
                for key, value in extra.items():
                    if key in {"events", "event_seq"}:
                        continue
                    record[key] = deepcopy(value)
            self._runs[run_id] = record
            self._persist()
            return self._public_run(record)

    def get_run(self, run_id: str) -> dict | None:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                return None
            return self._public_run(record)

    def get_internal_run(self, run_id: str) -> dict | None:
        with self._lock:
            return self._runs.get(run_id)

    def list_runs(self, *, mode: str | None = None) -> list[dict]:
        with self._lock:
            runs = []
            for record in self._runs.values():
                if mode and record.get("mode") != mode:
                    continue
                runs.append(self._public_run(record))
            runs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
            return runs

    def append_event(self, run_id: str, *, event_type: str, message: str = "", data: dict | None = None) -> dict:
        with self._condition:
            record = self._runs[run_id]
            record["event_seq"] = int(record.get("event_seq", 0)) + 1
            event = {
                "id": record["event_seq"],
                "ts": _now_iso(),
                "type": event_type,
                "message": message,
                "data": data or {},
            }
            record["events"].append(event)
            record["updated_at"] = event["ts"]
            events_path = Path(record["run_dir"]) / "events.jsonl"
            try:
                with events_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            except Exception:
                pass
            self._persist()
            self._condition.notify_all()
            return deepcopy(event)

    def wait_for_events(self, run_id: str, *, after_id: int, timeout_s: float = 15.0) -> list[dict]:
        with self._condition:
            if run_id not in self._runs:
                return []

            def _has_new() -> bool:
                record = self._runs.get(run_id)
                if record is None:
                    return True
                return int(record.get("event_seq", 0)) > int(after_id)

            if not _has_new():
                self._condition.wait(timeout=timeout_s)
            record = self._runs.get(run_id)
            if record is None:
                return []
            events = [deepcopy(item) for item in record.get("events", []) if int(item.get("id", 0)) > int(after_id)]
            return events

    def update_status(self, run_id: str, *, status: str, error: str = "") -> None:
        with self._lock:
            record = self._runs[run_id]
            now = _now_iso()
            record["status"] = status
            record["updated_at"] = now
            if status == "running" and not record.get("started_at"):
                record["started_at"] = now
            if status in {"completed", "failed"}:
                record["finished_at"] = now
            if error:
                record["error"] = error
            self._persist()
        self.append_event(run_id, event_type=f"run.{status}", message=error or status, data={"status": status})

    def set_result(self, run_id: str, result: dict) -> None:
        with self._lock:
            record = self._runs[run_id]
            record["result"] = deepcopy(result)
            record["updated_at"] = _now_iso()
            self._persist()

    def add_artifact(
        self,
        run_id: str,
        *,
        name: str,
        label: str,
        path: Path,
        content_type: str,
    ) -> dict:
        artifact = {
            "name": name,
            "label": label,
            "path": str(path),
            "filename": path.name,
            "size_bytes": _artifact_size(path),
            "content_type": content_type,
        }
        with self._lock:
            record = self._runs[run_id]
            artifacts = record.setdefault("artifacts", {})
            artifacts[name] = artifact
            record["updated_at"] = _now_iso()
            self._persist()
        self.append_event(run_id, event_type="run.artifact.ready", message=label, data={"artifact": name})
        return deepcopy(artifact)

    def get_artifact(self, run_id: str, artifact_name: str) -> dict | None:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                return None
            artifact = record.get("artifacts", {}).get(artifact_name)
            if not isinstance(artifact, dict):
                return None
            return deepcopy(artifact)

    def _public_run(self, record: dict) -> dict:
        payload = {key: deepcopy(value) for key, value in record.items() if key != "events"}
        payload["event_count"] = int(record.get("event_seq", 0))
        payload["events"] = [deepcopy(item) for item in record.get("events", [])]
        artifacts = payload.get("artifacts", {})
        if isinstance(artifacts, dict):
            payload["artifacts"] = [deepcopy(item) for item in artifacts.values()]
            payload["artifacts"].sort(key=lambda item: item.get("name", ""))
        return payload


_STORES: dict[str, RunStore] = {}
_STORE_LOCK = threading.Lock()


def get_run_store(root_dir: str) -> RunStore:
    resolved_root = str(Path(root_dir).resolve())
    with _STORE_LOCK:
        store = _STORES.get(resolved_root)
        if store is None:
            store = RunStore(resolved_root)
            _STORES[resolved_root] = store
        return store
