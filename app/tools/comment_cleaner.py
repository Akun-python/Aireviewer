from __future__ import annotations

import re

# Locator tokens that appear in internal comments, e.g. "P2-S1：..." or "P2-整段：...".
_P_SENTENCE_PATTERN = re.compile(r"[Pp]\s*(\d+)\s*-\s*[Ss]\s*(\d+)\s*[:：]?")
_P_PARAGRAPH_PATTERN = re.compile(r"[Pp]\s*(\d+)\s*-\s*整段\s*[:：]?")
_CH_PARAGRAPH_SENTENCE_PATTERN = re.compile(
    r"(?:正文\s*)?第\s*(\d+)\s*段\s*第\s*(\d+)\s*句\s*[:：]?"
)
_CH_PARAGRAPH_PATTERN = re.compile(
    r"(?:正文\s*)?第\s*(\d+)\s*段(?!\s*第\s*\d+\s*句)\s*[:：]?"
)
_SENTENCE_ONLY_PATTERN = re.compile(r"(?<!段)第\s*(\d+)\s*句\s*[:：]?")
_PARAGRAPH_ONLY_PATTERN = re.compile(r"整段\s*[:：]?")
_PARAGRAPH_LABEL_PATTERN = re.compile(r"^段落\s*[:：]?\s*")


def _format_paragraph(paragraph_index: int) -> str:
    # paragraph_index is zero-based internally
    return f"第{paragraph_index + 1}段"


def _convert_locators(segment: str) -> str:
    value = (segment or "").strip()
    if not value:
        return ""

    # Replace explicit P#-S# and P#-整段 first.
    def _replace_sentence(match: re.Match) -> str:
        paragraph_index = int(match.group(1))
        sentence_index = int(match.group(2))
        return f"{_format_paragraph(paragraph_index)}第{sentence_index}句："

    def _replace_paragraph(match: re.Match) -> str:
        paragraph_index = int(match.group(1))
        return f"{_format_paragraph(paragraph_index)}："

    value = _P_SENTENCE_PATTERN.sub(_replace_sentence, value)
    value = _P_PARAGRAPH_PATTERN.sub(_replace_paragraph, value)

    # Normalize Chinese paragraph/sentence markers.
    value = _CH_PARAGRAPH_SENTENCE_PATTERN.sub(
        lambda m: f"第{int(m.group(1))}段第{int(m.group(2))}句：",
        value,
    )
    value = _CH_PARAGRAPH_PATTERN.sub(lambda m: f"第{int(m.group(1))}段：", value)

    # Normalize sentence-only / paragraph-only markers.
    value = _SENTENCE_ONLY_PATTERN.sub(lambda m: f"本段第{int(m.group(1))}句：", value)
    value = _PARAGRAPH_ONLY_PATTERN.sub("本段：", value)
    value = _PARAGRAPH_LABEL_PATTERN.sub("本段：", value)
    value = re.sub(r"^[:：\s]+", "", value).strip()
    return value


def clean_comment_text(comment: str) -> str:
    """
    Convert internal locator tokens into readable Chinese labels for users.

    Examples:
    - "P2-S1：..." -> "第3段第1句：..."
    - "P2-整段：..." -> "第3段：..."
    - "第1句：..." -> "本段第1句：..."
    - "整段：..." -> "本段：..."
    """
    text = (comment or "").strip()
    if not text:
        return ""

    parts = re.split(r"[；;\n]+", text)
    cleaned_parts: list[str] = []
    for part in parts:
        cleaned = _convert_locators(part)
        if cleaned:
            cleaned_parts.append(cleaned)
    return "；".join(cleaned_parts).strip()
