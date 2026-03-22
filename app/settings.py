from __future__ import annotations

from dataclasses import dataclass
import os
import uuid


DEFAULT_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_API_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "openai:deepseek-chat"


def _strip_inline_comment(value: str) -> str:
    in_single = False
    in_double = False
    for idx, char in enumerate(value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            return value[:idx]
    return value


def _load_dotenv() -> None:
    root = (os.getenv("AGENT_ROOT_DIR") or DEFAULT_ROOT_DIR).strip() or DEFAULT_ROOT_DIR
    env_path = os.path.join(root, ".env")
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8-sig") as handle:
            lines = handle.readlines()
    except Exception:
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = _strip_inline_comment(value).strip().strip('"').strip("'").strip()
        if not value:
            continue
        os.environ.setdefault(key, value)


def _model_provider(model: str) -> str:
    value = (model or "").strip()
    if not value:
        return ""
    if ":" not in value:
        return "openai"
    return value.split(":", 1)[0].strip().lower()


@dataclass
class AppSettings:
    model: str
    api_base_url: str | None
    api_key: str | None
    root_dir: str
    skills_dir: str | None
    memory_files: list[str]
    use_store: bool
    revision_engine: str
    thread_id: str
    auto_approve: bool
    persist_sessions: bool
    checkpoint_path: str | None
    format_profile: str

    def apply_api_env(self) -> None:
        if _model_provider(self.model) != "openai":
            return
        if self.api_key:
            os.environ.setdefault("OPENAI_API_KEY", self.api_key)
        if self.api_base_url:
            os.environ.setdefault("OPENAI_BASE_URL", self.api_base_url)
            os.environ.setdefault("OPENAI_API_BASE", self.api_base_url)
        if not os.getenv("OPENAI_API_KEY", "").strip():
            raise RuntimeError("OPENAI_API_KEY is not set (configure API_KEY/OPENAI_API_KEY in env or .env)")

    @staticmethod
    def from_env() -> "AppSettings":
        return _build_settings_from_env()

def _default_state_dir(root_dir: str) -> str:
    return os.path.join(root_dir, "workspace", "agent_state")


def _read_thread_id(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = handle.read().strip()
            return value or None
    except Exception:
        return None


def _write_thread_id(path: str, thread_id: str) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(thread_id)
    except Exception:
        return


def _build_settings_from_env() -> AppSettings:
    _load_dotenv()
    model = os.getenv("LLM_MODEL", DEFAULT_MODEL)
    api_base_url = (
        os.getenv("API_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("OPENAI_API_BASE")
        or DEFAULT_API_BASE_URL
    )
    api_key = (os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip() or None
    root_dir = (os.getenv("AGENT_ROOT_DIR") or DEFAULT_ROOT_DIR).strip() or DEFAULT_ROOT_DIR
    skills_dir = os.getenv("AGENT_SKILLS_DIR")
    memory_files = os.getenv("AGENT_MEMORY_FILES", "").split(",")
    memory_files = [p.strip() for p in memory_files if p.strip()]
    use_store = os.getenv("AGENT_USE_STORE", "false").lower() in {"1", "true", "yes"}
    revision_engine = os.getenv("REVISION_ENGINE", "win32com")
    persist_sessions = os.getenv("AGENT_PERSIST_SESSIONS", "true").lower() in {"1", "true", "yes"}
    state_dir = os.getenv("AGENT_STATE_DIR", "").strip() or _default_state_dir(root_dir)
    thread_id_path = os.path.join(state_dir, "thread_id.txt")
    env_thread_id = os.getenv("AGENT_THREAD_ID", "").strip()
    if env_thread_id:
        thread_id = env_thread_id
        if persist_sessions:
            _write_thread_id(thread_id_path, thread_id)
    elif persist_sessions:
        thread_id = _read_thread_id(thread_id_path) or str(uuid.uuid4())
        _write_thread_id(thread_id_path, thread_id)
    else:
        thread_id = str(uuid.uuid4())
    checkpoint_path = os.getenv("AGENT_CHECKPOINT_PATH", "").strip()
    if not checkpoint_path and persist_sessions:
        checkpoint_path = os.path.join(state_dir, "checkpoints.sqlite")
    if not persist_sessions:
        checkpoint_path = ""
    auto_approve = os.getenv("AGENT_AUTO_APPROVE", "true").lower() in {"1", "true", "yes"}
    format_profile = os.getenv("FORMAT_PROFILE", "none").strip() or "none"

    return AppSettings(
        model=model,
        api_base_url=api_base_url,
        api_key=api_key,
        root_dir=root_dir,
        skills_dir=skills_dir,
        memory_files=memory_files,
        use_store=use_store,
        revision_engine=revision_engine,
        thread_id=thread_id,
        auto_approve=auto_approve,
        persist_sessions=persist_sessions,
        checkpoint_path=checkpoint_path or None,
        format_profile=format_profile,
    )


def load_settings() -> AppSettings:
    return _build_settings_from_env()
