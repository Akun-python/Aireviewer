from __future__ import annotations

import os
from typing import Literal

from langchain.tools import tool


def _build_client():
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY is not set")
    try:
        from tavily import TavilyClient  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("tavily package is not installed") from exc
    return TavilyClient(api_key=api_key)


def run_internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search using Tavily API (plain function for direct calls)."""
    client = _build_client()
    return client.search(
        query=query,
        max_results=max_results,
        topic=topic,
        include_raw_content=include_raw_content,
    )


@tool("internet_search")
def internet_search_tool(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search using Tavily API."""
    try:
        client = _build_client()
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
    return client.search(
        query=query,
        max_results=max_results,
        topic=topic,
        include_raw_content=include_raw_content,
    )
