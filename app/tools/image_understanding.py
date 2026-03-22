from __future__ import annotations

import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Any


DEFAULT_IMAGE_API_URL = "https://api.apiyi.com/v1/chat/completions"
DEFAULT_IMAGE_MODEL = "gpt-4o"


def _image_to_base64(image_path: str | Path) -> str:
    path = Path(image_path)
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _guess_mime(image_path: str | Path) -> str:
    mime = mimetypes.guess_type(str(image_path))[0]
    return mime or "application/octet-stream"


def _extract_first_message_content(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return content if isinstance(content, str) else ""


def analyze_image_apiyi(
    image_path: str | Path,
    *,
    prompt: str = "描述分析这张图",
    model: str | None = None,
    api_url: str | None = None,
    api_key: str | None = None,
    timeout_s: float = 90.0,
) -> dict[str, Any]:
    """
    Analyze an image using an OpenAI-compatible chat completions endpoint (APIYI).

    Env vars:
      - APIYI_API_KEY: required unless api_key is passed
      - APIYI_IMAGE_API_URL: optional override for api_url
      - APIYI_IMAGE_MODEL: optional override for model
    """
    resolved_model = (model or os.getenv("APIYI_IMAGE_MODEL", "") or DEFAULT_IMAGE_MODEL).strip()
    resolved_url = (api_url or os.getenv("APIYI_IMAGE_API_URL", "") or DEFAULT_IMAGE_API_URL).strip()
    resolved_key = (api_key or os.getenv("APIYI_API_KEY", "")).strip()
    if not resolved_key:
        return {"error": "APIYI_API_KEY is not set"}

    mime = _guess_mime(image_path)
    base64_image = _image_to_base64(image_path)
    payload = {
        "model": resolved_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt or "描述分析这张图"},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64_image}"}},
                ],
            }
        ],
    }
    headers = {
        "Authorization": resolved_key,
        "Content-Type": "application/json",
    }

    try:
        import requests  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return {"error": f"requests is not installed: {exc}"}

    try:
        resp = requests.post(resolved_url, headers=headers, json=payload, timeout=timeout_s)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}

    content = _extract_first_message_content(data)
    result: dict[str, Any] = {
        "provider": "apiyi",
        "model": resolved_model,
        "prompt": prompt,
        "content": content,
    }
    raw_mode = os.getenv("APIYI_IMAGE_INCLUDE_RAW", "").strip().lower() in {"1", "true", "yes"}
    if raw_mode:
        # Raw payload can be large; keep it behind a flag.
        result["raw"] = data
    # Attempt to parse JSON content if the model returns a JSON string.
    try:
        parsed = json.loads(content)
    except Exception:
        parsed = None
    if parsed is not None:
        result["parsed"] = parsed
    return result

