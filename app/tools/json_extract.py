from __future__ import annotations

import json


def extract_json_list(text: str) -> list | None:
    """
    Best-effort extract the first JSON list from free-form model output.

    Returns None when no JSON list can be found/parsed.
    """
    if not text:
        return None

    decoder = json.JSONDecoder()
    stripped = text.strip()

    try:
        direct = json.loads(stripped)
    except Exception:
        direct = None
    if isinstance(direct, list):
        return direct

    start = 0
    while True:
        idx = stripped.find("[", start)
        if idx == -1:
            break
        try:
            value, _end = decoder.raw_decode(stripped[idx:])
        except Exception:
            start = idx + 1
            continue
        if isinstance(value, list):
            return value
        start = idx + 1

    return None


def extract_json_object(text: str) -> dict | None:
    """
    Best-effort extract the first JSON object from free-form model output.

    Returns None when no JSON object can be found/parsed.
    """
    if not text:
        return None

    decoder = json.JSONDecoder()
    stripped = text.strip()

    try:
        direct = json.loads(stripped)
    except Exception:
        direct = None
    if isinstance(direct, dict):
        return direct

    start = 0
    while True:
        idx = stripped.find("{", start)
        if idx == -1:
            break
        try:
            value, _end = decoder.raw_decode(stripped[idx:])
        except Exception:
            start = idx + 1
            continue
        if isinstance(value, dict):
            return value
        start = idx + 1

    return None

