from __future__ import annotations

import re

from docx import Document

_PUNCTUATION = "。！？；：，、,.!?;:"
_SPACE_RE = re.compile(r"(?<=\S)[ \t]{2,}(?=\S)")
_SPACE_BEFORE_PUNCT_RE = re.compile(rf"[ \t]+([{re.escape(_PUNCTUATION)}])")
_DUP_PUNCT_RE = re.compile(rf"([{re.escape(_PUNCTUATION)}])\1+")


def _is_in_table(para) -> bool:
    try:
        return bool(para._p.xpath("./ancestor::w:tbl"))
    except Exception:
        return False


def normalize_paragraph(text: str) -> tuple[str, list[str]]:
    original = text or ""
    if not original:
        return original, []

    match_prefix = re.match(r"^\s+", original)
    match_suffix = re.search(r"\s+$", original)
    prefix = match_prefix.group(0) if match_prefix else ""
    suffix = match_suffix.group(0) if match_suffix else ""
    core = original[len(prefix) : (len(original) - len(suffix) if suffix else len(original))]
    if not core:
        return original, []

    reasons: list[str] = []

    collapsed_space = _SPACE_RE.sub(" ", core)
    if collapsed_space != core:
        reasons.append("合并多余空格")
        core = collapsed_space

    trimmed_punct_space = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", core)
    if trimmed_punct_space != core:
        reasons.append("删除标点前空格")
        core = trimmed_punct_space

    collapsed_punct = _DUP_PUNCT_RE.sub(r"\1", core)
    if collapsed_punct != core:
        reasons.append("合并重复标点")
        core = collapsed_punct

    normalized_text = f"{prefix}{core}{suffix}"
    if normalized_text == original:
        return original, []

    seen = set()
    ordered: list[str] = []
    for reason in reasons:
        key = (reason or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    if not ordered:
        ordered = ["格式规范化"]
    return normalized_text, ordered


def build_fallback_plan(input_path: str) -> list[dict]:
    doc = Document(input_path)
    plan: list[dict] = []
    body_index = 0
    for para in doc.paragraphs:
        if _is_in_table(para):
            continue
        original = para.text or ""
        stripped = original.strip()
        if not stripped:
            body_index += 1
            continue
        revised, reasons = normalize_paragraph(original)
        if revised != original and reasons:
            plan.append(
                {
                    "action": "replace",
                    "paragraph_index": body_index,
                    "content": revised,
                    "comment": "；".join(reasons),
                }
            )
        body_index += 1
    return plan

