from __future__ import annotations

import os
from pathlib import Path

from app.formatting.profiles import PROFILES
from app.tools.path_utils import ensure_workspace_dir


def has_win32() -> bool:
    if os.name != "nt":
        return False
    try:
        import pythoncom  # type: ignore  # noqa: F401
        import win32com  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def has_python_docx() -> bool:
    try:
        import docx  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def has_langgraph_sqlite() -> bool:
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip() or os.getenv("API_KEY", "").strip())


def has_tavily_key() -> bool:
    return bool(os.getenv("TAVILY_API_KEY", "").strip())


def has_apiyi_key() -> bool:
    return bool(os.getenv("APIYI_API_KEY", "").strip())


def get_capabilities(root_dir: str) -> dict:
    root = Path(root_dir).resolve()
    workspace = ensure_workspace_dir()
    win32_enabled = has_win32()
    python_docx_enabled = has_python_docx()
    template_path = root / "templates" / "正大杯报告格式.dotx"
    format_profiles: list[dict] = []
    for profile in PROFILES:
        available = True
        reason = ""
        if profile.key != "none" and not win32_enabled:
            available = False
            reason = "Requires Win32 Word"
        if profile.key == "zhengda_cup" and not template_path.exists():
            available = False
            reason = "Missing 正大杯报告格式.dotx template"
        format_profiles.append(
            {
                "key": profile.key,
                "label": profile.label,
                "available": available,
                "reason": reason,
            }
        )

    engine_options: list[dict] = [{"key": "auto", "label": "自动(推荐)", "available": True, "reason": ""}]
    engine_options.append(
        {
            "key": "win32com",
            "label": "Win32 Word",
            "available": win32_enabled,
            "reason": "" if win32_enabled else "pywin32 or Microsoft Word is unavailable",
        }
    )
    engine_options.append(
        {
            "key": "python-docx",
            "label": "python-docx",
            "available": python_docx_enabled,
            "reason": "" if python_docx_enabled else "python-docx is not installed",
        }
    )

    return {
        "root_dir": str(root),
        "workspace_dir": str(workspace),
        "features": {
            "win32": win32_enabled,
            "python_docx": python_docx_enabled,
            "langgraph_sqlite": has_langgraph_sqlite(),
            "openai_key": has_openai_key(),
            "tavily_key": has_tavily_key(),
            "apiyi_key": has_apiyi_key(),
        },
        "review": {
            "engines": engine_options,
            "format_profiles": format_profiles,
            "memory_scopes": [
                {"key": "document", "label": "按文档(跨次审阅·推荐)"},
                {"key": "run", "label": "仅本次(跨分段)"},
                {"key": "off", "label": "关闭(每段独立·最快)"},
                {"key": "session", "label": "会话(所有文档共享)"},
            ],
            "inline_context_modes": [
                {"key": "boundary", "label": "仅首/尾段落(推荐)"},
                {"key": "none", "label": "不内联(最省 token)"},
                {"key": "all", "label": "每段都带相邻上下文(最耗 token)"},
            ],
            "expansion_levels": [
                {"key": "none", "label": "不扩充"},
                {"key": "light", "label": "轻量扩充"},
                {"key": "heavy", "label": "大量扩充"},
            ],
        },
    }

