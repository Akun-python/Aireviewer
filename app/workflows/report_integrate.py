from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil

from app.agents.supervisor import build_agent
from app.formatting.auto_captions import apply_auto_captions
from app.formatting.profiles import apply_format_profile, resolve_profile
from app.settings import AppSettings
from app.tools.doc_map import IndexedSection, build_indexed_sections
from app.tools.path_utils import ensure_parent, resolve_path, to_virtual_path
from app.tools.win32_utils import (
    com_retry,
    dispatch_word_application,
    install_ole_message_filter,
    is_com_call_rejected,
    is_com_not_initialized,
    restore_ole_message_filter,
    try_fix_gen_py_cache,
)


@dataclass
class ChapterDigest:
    path: Path
    title: str
    outline: list[str]
    sample_text: str
    summary: str = ""
    key_points: list[str] | None = None


def _normalize_heading_text(text: str) -> str:
    value = (text or "").strip()
    value = re.sub(r"^\s*第[一二三四五六七八九十零〇两0-9]+[章节篇部分]\s*", "", value)
    value = re.sub(r"^\s*\d+(?:\.\d+)*[.\u3001)]\s*", "", value)
    value = re.sub(r"^\s*[一二三四五六七八九十]+[.\u3001)]\s*", "", value)
    value = re.sub(r"^\s*[（(][一二三四五六七八九十]+[)）]\s*", "", value)
    return value.strip()


def _safe_topic_from_paths(chapters: list[Path]) -> str:
    if not chapters:
        return "整合报告"
    stem = chapters[0].stem.strip()
    stem = re.sub(r"[^\w\u4e00-\u9fff\-]+", " ", stem).strip()
    return stem or "整合报告"


def _truncate(text: str, *, max_chars: int) -> str:
    value = text or ""
    if len(value) <= max_chars:
        return value
    return value[: max(0, max_chars)].rstrip() + "…"


def _build_outline_lines(sections: list[IndexedSection], *, max_lines: int = 80) -> list[str]:
    lines: list[str] = []
    for section in sections:
        if section.level and section.title:
            title = _normalize_heading_text(section.title)
            if title:
                lines.append(f"L{section.level} {title}")
        if len(lines) >= max_lines:
            break
    return lines[:max_lines]


def _build_sample_text(sections: list[IndexedSection], *, max_chars: int = 4500) -> str:
    parts: list[str] = []
    for section in sections:
        if section.level and section.title:
            title = _normalize_heading_text(section.title)
            if title:
                parts.append(title)
        for para in section.paragraphs:
            text = (para.text or "").strip()
            if not text:
                continue
            parts.append(text)
            if sum(len(p) for p in parts) >= max_chars:
                break
        if sum(len(p) for p in parts) >= max_chars:
            break
    return _truncate("\n".join(parts).strip(), max_chars=max_chars)


def _infer_chapter_title(path: Path, sections: list[IndexedSection]) -> str:
    for section in sections:
        if section.level == 1 and section.title:
            title = _normalize_heading_text(section.title)
            if title:
                return title
    stem = re.sub(r"^[0-9]+[_\-\s]*", "", path.stem).strip()
    return stem or path.stem


def _extract_json_object(text: str) -> dict | None:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        data = json.loads(candidate)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _invoke_agent(agent, prompt: str, *, thread_id: str) -> str:
    payload = {"messages": [{"role": "user", "content": prompt}]}
    result = agent.invoke(payload, config={"configurable": {"thread_id": thread_id}})
    content = result["messages"][-1].content if result and result.get("messages") else ""
    return (content or "").strip()


def _build_chapter_summary_prompt(topic: str, chapter: ChapterDigest) -> str:
    outline_text = "\n".join(chapter.outline)
    return (
        "你是“报告整合与目录框架构建”助手。"
        "请基于给定章节的标题、目录要点与正文样本，输出严格 JSON，不要 Markdown，不要解释。\n"
        "要求：\n"
        '1) summary: 200-350字中文摘要，强调本章解决什么问题、结论/发现、与全文关系。\n'
        "2) key_points: 5-8条要点，每条 18-40字。\n"
        "3) 禁止编造具体数据/政策原文；若缺失，用“需要补充：...”标注。\n"
        "JSON schema:\n"
        '{"summary": "...", "key_points": ["..."]}\n\n'
        f"报告主题：{topic}\n"
        f"章节标题：{chapter.title}\n"
        "章节目录线索：\n"
        f"{outline_text}\n\n"
        "章节正文样本：\n"
        f"{chapter.sample_text}\n"
    )


def _build_integration_prompt(topic: str, chapters: list[ChapterDigest]) -> str:
    items: list[str] = []
    for idx, ch in enumerate(chapters, start=1):
        points = ch.key_points or []
        bullets = "\n".join([f"- {p}" for p in points[:10]])
        items.append(
            "\n".join(
                [
                    f"[Chapter {idx}] {ch.title}",
                    f"摘要：{ch.summary}",
                    "要点：",
                    bullets or "- （无）",
                ]
            )
        )
    joined = "\n\n".join(items)
    return (
        "你是“报告整合与目录框架构建（自动图表编号、标题格式设置、章节之间逻辑连接）”智能体。"
        "现在已有若干章节内容的摘要与要点，请完成整合与逻辑连接设计，并输出严格 JSON。\n"
        "任务：\n"
        "A) 生成第一章《引言》，包含4个二级小节：研究背景、研究内容、研究方法、研究意义。每小节 220-420字。\n"
        "B) 为相邻章节生成过渡段 transitions：每段 120-200字，承上启下，点出上一章关键结论与下一章切入点。\n"
        "C) 给出 recommended_order：章节标题的推荐顺序（若与输入一致则原样输出）。\n"
        "约束：不得虚构具体数据/文献；用概括性表达；语言学术、连贯。\n"
        "JSON schema:\n"
        "{\n"
        '  "introduction": {"研究背景": "...", "研究内容": "...", "研究方法": "...", "研究意义": "..."},\n'
        '  "transitions": [{"from": "...", "to": "...", "text": "..."}],\n'
        '  "recommended_order": ["..."]\n'
        "}\n\n"
        f"报告主题：{topic}\n\n"
        "章节摘要与要点：\n"
        f"{joined}\n"
    )

def _fallback_chapter_summary(chapter: ChapterDigest) -> tuple[str, list[str]]:
    outline = [line.replace("L1 ", "").replace("L2 ", "").replace("L3 ", "") for line in chapter.outline]
    outline = [o for o in outline if o]
    points = outline[:8] if outline else []
    if not points:
        sample_lines = [line.strip() for line in (chapter.sample_text or "").splitlines() if line.strip()]
        points = sample_lines[:6]
    summary = "本章围绕“{title}”展开，梳理相关概念与核心问题，形成阶段性结论，并为后续章节的展开提供依据与铺垫。".format(
        title=chapter.title
    )
    points = [p[:38] for p in points if p][:8]
    if not points:
        points = ["需要补充：章节关键要点未能从文本中自动提取。"]
    return summary, points


def _fallback_integration(topic: str, chapters: list[ChapterDigest]) -> dict:
    intro = {
        "研究背景": f"围绕“{topic}”，本报告在既有研究与现实需求的交汇处提出问题意识，强调研究对象的时代情境与实践挑战，指出开展系统分析与对策建议的必要性。",
        "研究内容": "报告以章节为单元展开：先界定概念与研究范围，再梳理现状与问题结构，进一步提出分析框架与实施路径，最后形成综合性结论与建议，力求做到“问题—分析—对策”闭环。",
        "研究方法": "综合采用文献梳理、理论分析与案例/材料归纳等方法，必要时辅以比较分析与结构化框架建模；在写作上注重证据链与逻辑链一致，避免结论先行。",
        "研究意义": "理论上有助于深化对研究对象的机制性理解；实践上为决策与工作提供可操作的路径建议；同时也为后续量化检验与扩展研究奠定结构化基础。",
    }
    transitions: list[dict[str, str]] = []
    for a, b in zip(chapters, chapters[1:]):
        transitions.append(
            {
                "from": a.title,
                "to": b.title,
                "text": f"在上一章对“{a.title}”的梳理基础上，下一章将进一步聚焦“{b.title}”。"
                "这种推进体现为从概念与现状的界定，转向机制分析与路径展开，从而使全文论证形成递进关系与闭环结构。",
            }
        )
    return {"introduction": intro, "transitions": transitions, "recommended_order": [c.title for c in chapters]}


def _resolve_style_name(doc, candidates: list[str]) -> str | None:
    for name in candidates:
        try:
            doc.Styles(name)
        except Exception:
            continue
        return name
    return None


def _win32_add_paragraph(doc, text: str, style_name: str | None) -> None:
    rng = doc.Range(doc.Content.End - 1, doc.Content.End - 1)
    para = doc.Paragraphs.Add(rng)
    para.Range.Text = text
    if style_name:
        try:
            para.Range.Style = style_name
        except Exception:
            pass


def _win32_insert_page_break(doc, constants) -> None:
    rng = doc.Range(doc.Content.End - 1, doc.Content.End - 1)
    try:
        # Prefer numeric WdBreakType to avoid win32com constants/gen_py issues.
        try:
            rng.InsertBreak(7)  # wdPageBreak
        except Exception:
            rng.InsertBreak()
    except Exception:
        try:
            rng.InsertParagraphAfter()
        except Exception:
            pass


def _win32_heading_level(para, constants) -> int | None:
    try:
        rng = para.Range
    except Exception:
        return None
    style_name = ""
    try:
        style = rng.Style
        style_name = str(getattr(style, "NameLocal", "") or getattr(style, "Name", ""))
    except Exception:
        style_name = ""
    name = (style_name or "").strip().lower()
    if name in {"title", "标题"}:
        return 1
    if name.startswith("heading"):
        parts = re.split(r"\s+", style_name.strip())
        if len(parts) >= 2 and parts[1].isdigit():
            return int(parts[1])
        match = re.search(r"heading\s*(\d+)", name)
        if match:
            return int(match.group(1))
        return 1
    if style_name.strip().startswith("标题"):
        parts = re.split(r"\s+", style_name.strip())
        if len(parts) >= 2 and parts[1].isdigit():
            return int(parts[1])
        match = re.search(r"标题\s*(\d+)", style_name)
        if match:
            return int(match.group(1))
        return 1
    if constants is not None:
        try:
            lvl = int(getattr(para, "OutlineLevel", 0))
            if lvl in {
                getattr(constants, "wdOutlineLevel1", 1),
                getattr(constants, "wdOutlineLevel2", 2),
                getattr(constants, "wdOutlineLevel3", 3),
                4,
                5,
            }:
                return int(lvl)
        except Exception:
            return None
    return None


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n{2,}", text or "") if p.strip()]


def _win32_insert_paragraphs_at(doc, *, pos: int, paragraphs: list[str], style_name: str | None) -> None:
    insert_rng = doc.Range(int(pos), int(pos))
    for paragraph in paragraphs:
        para = doc.Paragraphs.Add(insert_rng)
        para.Range.Text = paragraph
        if style_name:
            try:
                para.Range.Style = style_name
            except Exception:
                pass
        try:
            para.Range.InsertParagraphAfter()
        except Exception:
            pass
        try:
            insert_rng = para.Range.Duplicate
            insert_rng.Start = insert_rng.End
            insert_rng.End = insert_rng.Start
        except Exception:
            insert_rng = doc.Range(int(pos), int(pos))


def _win32_insert_transition_between_h1_and_first_h2(
    doc,
    *,
    start: int,
    end: int,
    transition_text: str,
    normal_style: str | None,
    constants,
) -> bool:
    text = (transition_text or "").strip()
    if not text:
        return False
    try:
        chapter_rng = doc.Range(int(start), int(end))
        paras = chapter_rng.Paragraphs
        total = paras.Count
    except Exception:
        return False

    first_h1 = None
    first_h2 = None
    for idx in range(1, total + 1):
        para = paras(idx)
        lvl = _win32_heading_level(para, constants)
        if lvl == 1 and first_h1 is None:
            first_h1 = para
            continue
        if first_h1 is not None and lvl is not None and lvl >= 2:
            first_h2 = para
            break

    if first_h1 is None:
        return False

    insert_pos = None
    if first_h2 is not None:
        try:
            insert_pos = int(first_h2.Range.Start)
        except Exception:
            insert_pos = None
    if insert_pos is None:
        try:
            insert_pos = int(first_h1.Range.End)
        except Exception:
            return False

    paragraphs = _split_paragraphs(text)
    _win32_insert_paragraphs_at(doc, pos=insert_pos, paragraphs=paragraphs, style_name=normal_style)
    return True


def _win32_normalize_headings(doc, constants) -> None:
    total = getattr(doc.Paragraphs, "Count", 0) or 0
    for idx in range(1, total + 1):
        para = doc.Paragraphs(idx)
        rng = para.Range
        raw = (rng.Text or "").strip()
        if not raw:
            continue
        style_name = ""
        try:
            style = rng.Style
            style_name = str(getattr(style, "NameLocal", "") or getattr(style, "Name", ""))
        except Exception:
            style_name = ""
        is_heading = False
        if style_name:
            name = style_name.strip().lower()
            if name.startswith("heading") or style_name.strip().startswith("标题"):
                is_heading = True
        if not is_heading and constants is not None:
            try:
                level = int(getattr(para, "OutlineLevel", 0))
                is_heading = level in {
                    constants.wdOutlineLevel1,
                    constants.wdOutlineLevel2,
                    constants.wdOutlineLevel3,
                }
            except Exception:
                is_heading = False
        if not is_heading:
            continue
        cleaned = _normalize_heading_text(raw)
        if cleaned and cleaned != raw:
            try:
                target = rng.Duplicate
                target.End = max(int(target.Start), int(target.End) - 1)
                target.Text = cleaned
            except Exception:
                continue


def integrate_report_chapters(
    *,
    settings: AppSettings,
    chapter_paths: list[str],
    output_path: str,
    topic: str | None = None,
    toc_position: str = "after_title",
    format_profile: str | None = None,
    allow_llm: bool = True,
    auto_captions: bool = True,
    fixed_order: list[str] | None = None,
    logger=None,
) -> dict:
    output_real = resolve_path(output_path)
    ensure_parent(output_real)

    def _log(message: str) -> None:
        if logger:
            logger(message)

    chapter_files = [resolve_path(p) for p in chapter_paths if isinstance(p, str) and p.strip()]
    chapter_files = [p for p in chapter_files if p.exists()]
    if not chapter_files:
        raise ValueError("未提供有效的章节 Word 文件路径。")

    resolved_topic = (topic or "").strip() or _safe_topic_from_paths(chapter_files)
    _log(f"[integrate] topic={resolved_topic} chapters={len(chapter_files)}")

    digests: list[ChapterDigest] = []
    for path in chapter_files:
        sections = build_indexed_sections(str(path))
        title = _infer_chapter_title(path, sections)
        outline = _build_outline_lines(sections)
        sample_text = _build_sample_text(sections)
        digests.append(ChapterDigest(path=path, title=title, outline=outline, sample_text=sample_text))

    integration_payload: dict | None = None
    if allow_llm:
        try:
            system_prompt = "你是报告整合、结构优化与过渡写作助手。输出必须严格按用户要求的 JSON。"
            agent = build_agent(settings, tools=[], system_prompt=system_prompt)
            for idx, ch in enumerate(digests, start=1):
                prompt = _build_chapter_summary_prompt(resolved_topic, ch)
                thread_id = f"integrate_summary_{idx}_{dt.datetime.now().timestamp()}"
                raw = _invoke_agent(agent, prompt, thread_id=thread_id)
                data = _extract_json_object(raw)
                if not data:
                    summary, points = _fallback_chapter_summary(ch)
                else:
                    summary = (data.get("summary") or "").strip()
                    points = data.get("key_points") if isinstance(data.get("key_points"), list) else None
                    points = [str(p).strip() for p in (points or []) if str(p).strip()]
                    if not summary:
                        summary, points2 = _fallback_chapter_summary(ch)
                        points = points or points2
                ch.summary = summary
                ch.key_points = points[:10] if points else []
                _log(f"[summary] {idx}/{len(digests)} {ch.title} ({len(ch.summary)}字)")

            prompt = _build_integration_prompt(resolved_topic, digests)
            thread_id = f"integrate_all_{dt.datetime.now().timestamp()}"
            raw = _invoke_agent(agent, prompt, thread_id=thread_id)
            integration_payload = _extract_json_object(raw)
        except Exception as exc:  # noqa: BLE001
            _log(f"[llm] failed: {exc}")
            integration_payload = None

    integration = integration_payload if isinstance(integration_payload, dict) else _fallback_integration(resolved_topic, digests)
    introduction = integration.get("introduction") if isinstance(integration, dict) else None
    transitions = integration.get("transitions") if isinstance(integration, dict) else None
    recommended_order = integration.get("recommended_order") if isinstance(integration, dict) else None

    if not isinstance(introduction, dict):
        introduction = _fallback_integration(resolved_topic, digests)["introduction"]
    if not isinstance(transitions, list):
        transitions = _fallback_integration(resolved_topic, digests)["transitions"]
    if not isinstance(recommended_order, list):
        recommended_order = [ch.title for ch in digests]

    # Reorder chapters if model suggests a permutation that matches the set.
    by_title = {ch.title: ch for ch in digests}
    reordered: list[ChapterDigest] = []
    used: set[str] = set()
    order_source = fixed_order if fixed_order else recommended_order
    if isinstance(order_source, list):
        for title in order_source:
            if not isinstance(title, str):
                continue
            key = title.strip()
            if not key:
                continue
            # Match by chapter title, file stem, or filename.
            candidate = None
            if key in by_title:
                candidate = by_title[key]
            if candidate is None:
                for ch in digests:
                    if ch.path.stem == key or ch.path.name == key:
                        candidate = ch
                        break
            if candidate and candidate.title not in used:
                reordered.append(candidate)
                used.add(candidate.title)
    for ch in digests:
        if ch.title not in used:
            reordered.append(ch)

    # Write analysis artifact for debugging / traceability.
    analysis_path = output_real.with_suffix(".integration.json")
    try:
        analysis = {
            "topic": resolved_topic,
            "chapters": [
                {
                    "path": str(ch.path),
                    "title": ch.title,
                    "outline": ch.outline,
                    "summary": ch.summary,
                    "key_points": ch.key_points or [],
                }
                for ch in reordered
            ],
            "introduction": introduction,
            "transitions": transitions,
            "recommended_order": [ch.title for ch in reordered],
        }
        analysis_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        analysis_path = None

    if os.name != "nt":
        raise RuntimeError("章节整合当前仅实现 Win32 Word 引擎（需要 Windows + pywin32 + Word）。")

    try:
        import pythoncom  # type: ignore
        import win32com.client as win32  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"win32com 初始化失败：{exc}") from exc

    # Build transitions map for quick lookup.
    transition_map: dict[tuple[str, str], str] = {}
    for item in transitions:
        if not isinstance(item, dict):
            continue
        a = str(item.get("from") or "").strip()
        b = str(item.get("to") or "").strip()
        t = str(item.get("text") or "").strip()
        if a and b and t:
            transition_map[(a, b)] = t

    tmp_out = output_real.with_suffix(".tmp.docx")
    if tmp_out.exists():
        try:
            tmp_out.unlink()
        except Exception:
            pass

    pythoncom.CoInitialize()
    old_filter, message_filter = install_ole_message_filter()
    word = None
    doc = None
    try:
        # Best-effort repair for corrupted win32com.gen_py caches (common on Windows).
        try:
            try_fix_gen_py_cache(None, aggressive=True)
        except Exception:
            pass

        word = com_retry(dispatch_word_application)
        word.Visible = False
        word.DisplayAlerts = 0
        doc = com_retry(lambda: word.Documents.Add())
        constants = None

        title_style = _resolve_style_name(doc, ["Title", "标题"])
        h1_style = _resolve_style_name(doc, ["Heading 1", "标题 1"])
        h2_style = _resolve_style_name(doc, ["Heading 2", "标题 2"])
        normal_style = _resolve_style_name(doc, ["Normal", "正文"])

        first_para = doc.Paragraphs(1)
        first_para.Range.Text = f"{resolved_topic} 课题报告"
        if title_style:
            try:
                first_para.Range.Style = title_style
            except Exception:
                pass

        if toc_position == "before_outline":
            _win32_add_paragraph(doc, "报告大纲表", h1_style)
            # A lightweight outline list (avoid heavy tables by default).
            for idx, ch in enumerate(reordered, start=1):
                _win32_add_paragraph(doc, f"{idx}. {ch.title}", normal_style)

        # Chapter 1: Introduction
        _win32_insert_page_break(doc, constants)
        _win32_add_paragraph(doc, "引言", h1_style)
        for key in ["研究背景", "研究内容", "研究方法", "研究意义"]:
            _win32_add_paragraph(doc, key, h2_style)
            body = str(introduction.get(key, "") or "").strip()
            if not body:
                body = "需要补充：本节内容生成失败，请人工完善。"
            for paragraph in [p.strip() for p in re.split(r"\n{2,}", body) if p.strip()]:
                _win32_add_paragraph(doc, paragraph, normal_style)

        # Insert chapters and transitions.
        for idx, ch in enumerate(reordered):
            _win32_insert_page_break(doc, constants)
            insert_range = doc.Range(doc.Content.End - 1, doc.Content.End - 1)
            inserted_start = int(insert_range.Start)
            try:
                insert_range.InsertFile(str(ch.path))
            except Exception:
                # Fallback: copy the file to output even if insertion fails.
                raise RuntimeError(f"无法插入章节文件：{ch.path}")
            try:
                inserted_end = int(insert_range.End)
            except Exception:
                inserted_end = int(doc.Content.End - 1)

            # Insert transition paragraph into *this* chapter, between its H1 and first H2.
            # Use the transition from previous chapter -> current chapter.
            if idx > 0:
                prev_ch = reordered[idx - 1]
                text = transition_map.get((prev_ch.title, ch.title), "").strip()
                if text:
                    _win32_insert_transition_between_h1_and_first_h2(
                        doc,
                        start=inserted_start,
                        end=inserted_end,
                        transition_text=text,
                        normal_style=normal_style,
                        constants=constants,
                    )

        _win32_normalize_headings(doc, constants)

        try:
            doc.Fields.Update()
        except Exception:
            pass
        ensure_parent(tmp_out)
        com_retry(lambda: doc.SaveAs(str(tmp_out)))
    finally:
        if doc is not None:
            try:
                com_retry(lambda: doc.Close(SaveChanges=False), timeout_s=5.0)
            except Exception:
                pass
        if word is not None:
            try:
                com_retry(lambda: word.Quit(), timeout_s=5.0)
            except Exception:
                pass
        if message_filter is not None:
            restore_ole_message_filter(old_filter)
        pythoncom.CoUninitialize()

    # Apply formatting profile (TOC / numbering / fonts).
    os.environ["REPORT_TOC_POSITION"] = (toc_position or "after_title").strip()
    profile = (format_profile or os.getenv("REPORT_FORMAT_PROFILE", "")).strip() or "thesis_standard"
    profile = resolve_profile(profile)
    if profile != "none":
        try:
            apply_format_profile(docx_path=str(tmp_out), root_dir=settings.root_dir, profile=profile)
            _log(f"[format] profile={profile}")
        except Exception as exc:  # noqa: BLE001
            message = f"[format] failed: {exc}"
            if is_com_call_rejected(exc):
                message += "；Word 正忙或存在弹窗，建议关闭所有 Word 窗口/对话框后重试"
            elif is_com_not_initialized(exc):
                message += "；COM 未初始化（多线程调用需在该线程先 CoInitialize）"
            _log(message)

    if auto_captions:
        try:
            apply_auto_captions(
                docx_path=str(tmp_out),
                include_chapter_number=(profile != "none"),
                chapter_style_level=1,
                logger=_log,
            )
        except Exception as exc:  # noqa: BLE001
            _log(f"[captions] failed: {exc}")

    if output_real.exists():
        try:
            output_real.unlink()
        except Exception:
            pass
    shutil.move(str(tmp_out), str(output_real))

    return {
        "output_path": to_virtual_path(output_real),
        "analysis_path": to_virtual_path(analysis_path) if analysis_path and isinstance(analysis_path, Path) else "",
        "topic": resolved_topic,
        "chapters": [ch.title for ch in reordered],
    }
