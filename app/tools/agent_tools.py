from __future__ import annotations

import os
from pathlib import Path
try:
    from langchain.tools import tool
except Exception as exc:  # noqa: BLE001
    _LANGCHAIN_IMPORT_ERROR: Exception | None = exc

    def tool(_name: str):
        def _decorator(fn):
            return fn

        return _decorator
else:
    _LANGCHAIN_IMPORT_ERROR = None

from app.tools.doc_map import build_doc_map, extract_section_text
from app.tools.revision_engine import apply_revisions
from app.tools.path_utils import ensure_parent, resolve_path, to_virtual_path


@tool("build_doc_map")
def build_doc_map_tool(input_path: str, output_path: str = "") -> str:
    """Create a document map and return the map path."""
    return build_doc_map(input_path, output_path or None)


@tool("extract_section_text")
def extract_section_text_tool(input_path: str, section_index: int) -> str:
    """Extract text for a section index from the document map."""
    return extract_section_text(input_path, section_index)


@tool("apply_revisions")
def apply_revisions_tool(
    input_path: str,
    output_path: str,
    revisions_json: str,
    engine: str = "",
) -> str:
    """Apply revision instructions and return output path."""
    engine_value = (engine or "").strip()
    if not engine_value:
        engine_value = os.getenv("REVISION_ENGINE", "").strip() or "auto"
    return apply_revisions(input_path, output_path, revisions_json, engine_value)


@tool("save_revision_summary")
def save_revision_summary_tool(output_path: str, summary: str) -> str:
    """Write a revision summary to a text file and return the path."""
    output_real = resolve_path(output_path)
    if output_real.suffix.lower() == ".docx":
        output_real = output_real.with_suffix(".summary.txt")
    elif output_real.suffix == "":
        output_real = output_real.with_suffix(".summary.txt")
    ensure_parent(output_real)
    Path(output_real).write_text(summary, encoding="utf-8")
    return to_virtual_path(output_real)


def build_tools(*, allow_web_search: bool | None = None):
    if _LANGCHAIN_IMPORT_ERROR is not None:
        raise RuntimeError("缺少依赖 langchain，请先运行：pip install -r requirements.txt") from _LANGCHAIN_IMPORT_ERROR
    if allow_web_search is None:
        allow_web_search = os.getenv("ENABLE_WEB_SEARCH", "").lower() in {"1", "true", "yes"}
    tools = [
        build_doc_map_tool,
        extract_section_text_tool,
        apply_revisions_tool,
        save_revision_summary_tool,
    ]
    if not allow_web_search:
        return tools
    try:
        from app.tools.internet_search import internet_search_tool
    except Exception as exc:  # noqa: BLE001
        print(f"[tools] internet_search unavailable: {exc}")
        return tools
    tools.append(internet_search_tool)
    return tools


def build_plan_tools(*, allow_web_search: bool | None = None):
    """
    Build a minimal toolset for plan generation.

    Planning should not mutate documents or use file tools; optionally allow web search.
    """
    if _LANGCHAIN_IMPORT_ERROR is not None:
        raise RuntimeError("缺少依赖 langchain，请先运行：pip install -r requirements.txt") from _LANGCHAIN_IMPORT_ERROR
    if allow_web_search is None:
        allow_web_search = os.getenv("ENABLE_WEB_SEARCH", "").lower() in {"1", "true", "yes"}
    if not allow_web_search:
        return []
    try:
        from app.tools.internet_search import internet_search_tool
    except Exception as exc:  # noqa: BLE001
        print(f"[tools] internet_search unavailable: {exc}")
        return []
    return [internet_search_tool]
