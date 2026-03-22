from __future__ import annotations

import os

from app.settings import AppSettings
from app.tools.path_utils import ensure_parent, resolve_path


def _raise_missing_deps(exc: Exception) -> None:
    raise RuntimeError("缺少依赖，请先运行：pip install -r requirements.txt") from exc


def build_backend(settings: AppSettings):
    if settings.use_store:
        try:
            from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
            from langgraph.store.memory import InMemoryStore
        except Exception as exc:  # noqa: BLE001
            _raise_missing_deps(exc)
        store = InMemoryStore()
        backend = lambda rt: CompositeBackend(
            default=StateBackend(rt),
            routes={"/memories/": StoreBackend(rt)},
        )
        return backend, store

    try:
        from deepagents.backends import FilesystemBackend
    except Exception as exc:  # noqa: BLE001
        _raise_missing_deps(exc)
    backend = FilesystemBackend(root_dir=settings.root_dir, virtual_mode=True)
    return backend, None


def _build_checkpointer(settings: AppSettings):
    try:
        from langgraph.checkpoint.memory import MemorySaver
    except Exception as exc:  # noqa: BLE001
        _raise_missing_deps(exc)
    if not settings.persist_sessions or not settings.checkpoint_path:
        return MemorySaver()
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except Exception:
        return MemorySaver()
    try:
        checkpoint_path = resolve_path(settings.checkpoint_path)
        ensure_parent(checkpoint_path)
        # Prefer path-based constructor on Windows to avoid URI parsing edge cases
        # around drive letters like "C:". Fall back to conn-string when available.
        if os.name == "nt":
            try:
                return SqliteSaver(str(checkpoint_path))
            except Exception:
                pass
        conn_string = f"sqlite:///{checkpoint_path.as_posix()}"
        if hasattr(SqliteSaver, "from_conn_string"):
            try:
                return SqliteSaver.from_conn_string(conn_string)
            except Exception:
                return SqliteSaver(str(checkpoint_path))
        return SqliteSaver(str(checkpoint_path))
    except Exception:
        return MemorySaver()


def build_agent(settings: AppSettings, tools, system_prompt: str):
    try:
        from deepagents import create_deep_agent
    except Exception as exc:  # noqa: BLE001
        _raise_missing_deps(exc)
    settings.apply_api_env()
    backend, store = build_backend(settings)
    checkpointer = _build_checkpointer(settings)

    interrupt_on = {}
    if not settings.auto_approve:
        interrupt_on = {
            "apply_revisions": {"allowed_decisions": ["approve", "edit", "reject"]},
            "save_revision_summary": {"allowed_decisions": ["approve", "reject"]},
        }

    kwargs = {
        "model": settings.model,
        "tools": tools,
        "system_prompt": system_prompt,
        "backend": backend,
        "checkpointer": checkpointer,
        "interrupt_on": interrupt_on,
    }
    if store is not None:
        kwargs["store"] = store
    if settings.skills_dir:
        kwargs["skills"] = [settings.skills_dir]
    if settings.memory_files:
        kwargs["memory"] = settings.memory_files

    return create_deep_agent(**kwargs)

