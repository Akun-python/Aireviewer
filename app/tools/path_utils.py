from __future__ import annotations

from pathlib import Path
import os
import shutil
import uuid


_DEFAULT_ROOT_DIR = Path(__file__).resolve().parents[2]


def root_dir() -> Path:
    value = os.getenv("AGENT_ROOT_DIR", "").strip()
    if value:
        try:
            return Path(value).expanduser().resolve()
        except Exception:
            pass
    return _DEFAULT_ROOT_DIR


def resolve_path(path: str) -> Path:
    if path.startswith("/"):
        return (root_dir() / path.lstrip("/")).resolve()
    p = Path(path)
    if p.is_absolute():
        return p
    return (root_dir() / p).resolve()


def to_virtual_path(path: str | Path) -> str:
    if isinstance(path, str) and path.startswith("/"):
        return path
    p = Path(path).resolve()
    root = root_dir()
    try:
        rel = p.relative_to(root)
    except ValueError:
        return p.as_posix()
    return "/" + rel.as_posix()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def ensure_workspace_dir() -> Path:
    workspace = root_dir() / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def is_within_root(path: Path) -> bool:
    try:
        path.relative_to(root_dir())
    except ValueError:
        return False
    return True


def copy_to_workspace(source_path: str) -> Path:
    src = resolve_path(source_path)
    if not src.exists():
        raise FileNotFoundError(str(src))
    if is_within_root(src):
        return src
    workspace = ensure_workspace_dir() / "imports" / uuid.uuid4().hex
    workspace.mkdir(parents=True, exist_ok=True)
    dest = workspace / src.name
    shutil.copy2(src, dest)
    return dest
