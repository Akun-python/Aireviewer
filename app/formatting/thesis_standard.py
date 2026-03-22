from __future__ import annotations

import os
from pathlib import Path

from app.tools.win32_utils import (
    com_retry,
    dispatch_word_application_with_pid,
    get_win32_constants,
    install_ole_message_filter,
    restore_ole_message_filter,
)


def _cm_to_points(app, value: float) -> float:
    try:
        return float(app.CentimetersToPoints(value))
    except Exception:
        return float(value) * 28.3465


def _set_paragraph_format(pf, *, align=None, before=None, after=None, indent=None, spacing_rule=None, spacing=None):
    if align is not None:
        pf.Alignment = align
    if before is not None:
        pf.SpaceBefore = before
    if after is not None:
        pf.SpaceAfter = after
    if indent is not None:
        pf.FirstLineIndent = indent
    if spacing_rule is not None:
        pf.LineSpacingRule = spacing_rule
    if spacing is not None:
        pf.LineSpacing = spacing


def _apply_style(doc, name: str, *, font_fe: str, font_ascii: str, size: float, bold: bool,
                 align, before: float, after: float, indent: float, spacing_rule, spacing=None,
                 keep_with_next: bool = False) -> None:
    try:
        style = doc.Styles(name)
    except Exception:
        return
    try:
        font = style.Font
        font.NameFarEast = font_fe
        font.NameAscii = font_ascii
        font.Name = font_ascii
        font.Size = size
        font.Bold = bool(bold)
    except Exception:
        pass
    try:
        pf = style.ParagraphFormat
        _set_paragraph_format(
            pf,
            align=align,
            before=before,
            after=after,
            indent=indent,
            spacing_rule=spacing_rule,
            spacing=spacing,
        )
        pf.KeepWithNext = bool(keep_with_next)
    except Exception:
        pass


def _apply_multilevel_numbering(doc, constants, app) -> None:
    if constants is None:
        return
    try:
        gallery = doc.Application.ListGalleries(constants.wdOutlineNumberGallery)
        template = gallery.ListTemplates(1)
    except Exception:
        return

    def _level(level: int, fmt: str, linked_style: str, number_pos_cm: float, text_pos_cm: float):
        try:
            lvl = template.ListLevels(level)
            lvl.NumberFormat = fmt
            lvl.TrailingCharacter = constants.wdTrailingTab
            lvl.NumberStyle = constants.wdListNumberStyleArabic
            lvl.NumberPosition = _cm_to_points(app, number_pos_cm)
            lvl.TextPosition = _cm_to_points(app, text_pos_cm)
            lvl.ResetOnHigher = level - 1
            lvl.StartAt = 1
            lvl.LinkedStyle = linked_style
            lvl.Alignment = constants.wdListLevelAlignLeft
        except Exception:
            return

    _level(1, "%1.", "Heading 1", 0.0, 0.74)
    _level(2, "%1.%2.", "Heading 2", 0.74, 1.48)
    _level(3, "%1.%2.%3.", "Heading 3", 1.48, 2.2)

    def _link(style_name: str, level: int) -> None:
        try:
            doc.Styles(style_name).LinkToListTemplate(template, level=level)
        except Exception:
            return

    _link("Heading 1", 1)
    _link("标题 1", 1)
    _link("Heading 2", 2)
    _link("标题 2", 2)
    _link("Heading 3", 3)
    _link("标题 3", 3)


def _ensure_toc(doc, constants, app, position: str) -> None:
    try:
        if doc.TablesOfContents.Count > 0:
            for idx in range(1, doc.TablesOfContents.Count + 1):
                doc.TablesOfContents(idx).Update()
            return
    except Exception:
        pass

    insert_range = None
    if position == "before_outline":
        try:
            for para in doc.Paragraphs:
                if (para.Range.Text or "").strip() == "报告大纲表":
                    insert_range = para.Range
                    break
        except Exception:
            insert_range = None
    if insert_range is None:
        try:
            first_para = doc.Paragraphs(1)
            insert_range = doc.Range(first_para.Range.End, first_para.Range.End)
        except Exception:
            insert_range = doc.Range(0, 0)

    toc_heading_style = None
    for name in ("TOC Heading", "目录", "Heading 1", "标题 1"):
        try:
            doc.Styles(name)
        except Exception:
            continue
        toc_heading_style = name
        break

    para = doc.Paragraphs.Add(insert_range)
    para.Range.Text = "目录"
    if toc_heading_style:
        try:
            para.Range.Style = toc_heading_style
        except Exception:
            pass
    if constants is not None:
        try:
            para.OutlineLevel = constants.wdOutlineLevelBodyText
        except Exception:
            pass
    try:
        para.Range.InsertParagraphAfter()
    except Exception:
        pass
    toc_range = para.Range.Duplicate
    try:
        toc_range.Collapse(constants.wdCollapseEnd)
    except Exception:
        pass
    try:
        doc.TablesOfContents.Add(
            Range=toc_range,
            UseHeadingStyles=True,
            UpperHeadingLevel=1,
            LowerHeadingLevel=3,
            IncludePageNumbers=True,
            RightAlignPageNumbers=True,
        )
    except Exception:
        return


def apply_thesis_standard_profile(docx_path: str, root_dir: str) -> None:
    docx_real = str(Path(docx_path).resolve())
    if not os.path.exists(docx_real):
        raise FileNotFoundError(docx_real)
    try:
        import pythoncom  # type: ignore
        import win32com.client as win32  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"win32com 初始化失败：{exc}") from exc

    pythoncom.CoInitialize()
    old_filter, message_filter = install_ole_message_filter()
    word = None
    doc = None
    try:
        word, _word_pid = com_retry(dispatch_word_application_with_pid)
        word.Visible = False
        word.DisplayAlerts = 0
        try:
            word.Options.UpdateLinksAtOpen = False
        except Exception:
            pass
        try:
            word.Options.ConfirmConversions = False
        except Exception:
            pass
        try:
            word.Options.BackgroundSave = False
        except Exception:
            pass
        try:
            doc = com_retry(
                lambda: word.Documents.Open(
                    docx_real,
                    ConfirmConversions=False,
                    ReadOnly=False,
                    AddToRecentFiles=False,
                    Revert=False,
                    OpenAndRepair=True,
                    NoEncodingDialog=True,
                )
            )
        except TypeError:
            doc = com_retry(lambda: word.Documents.Open(docx_real))
        try:
            constants = get_win32_constants(win32)
        except Exception:
            constants = None

        app = com_retry(lambda: word.Application)
        ps = com_retry(lambda: doc.PageSetup)

        def _set_pagesetup(name: str, value) -> None:
            try:
                com_retry(lambda: setattr(ps, name, value))
            except Exception:
                pass

        if constants:
            _set_pagesetup("PaperSize", constants.wdPaperA4)
        _set_pagesetup("TopMargin", _cm_to_points(app, 2.5))
        _set_pagesetup("BottomMargin", _cm_to_points(app, 2.5))
        _set_pagesetup("LeftMargin", _cm_to_points(app, 3.0))
        _set_pagesetup("RightMargin", _cm_to_points(app, 2.5))
        _set_pagesetup("HeaderDistance", _cm_to_points(app, 1.5))
        _set_pagesetup("FooterDistance", _cm_to_points(app, 1.5))

        line_rule = constants.wdLineSpace1pt5 if constants else 1
        align_justify = constants.wdAlignParagraphJustify if constants else 3
        align_left = constants.wdAlignParagraphLeft if constants else 0
        align_center = constants.wdAlignParagraphCenter if constants else 1

        _apply_style(
            doc,
            "Normal",
            font_fe="宋体",
            font_ascii="Times New Roman",
            size=12,
            bold=False,
            align=align_justify,
            before=0,
            after=0,
            indent=24,
            spacing_rule=line_rule,
            keep_with_next=False,
        )
        _apply_style(
            doc,
            "Title",
            font_fe="黑体",
            font_ascii="Times New Roman",
            size=18,
            bold=True,
            align=align_center,
            before=12,
            after=12,
            indent=0,
            spacing_rule=line_rule,
            keep_with_next=True,
        )
        _apply_style(
            doc,
            "标题",
            font_fe="黑体",
            font_ascii="Times New Roman",
            size=18,
            bold=True,
            align=align_center,
            before=12,
            after=12,
            indent=0,
            spacing_rule=line_rule,
            keep_with_next=True,
        )
        _apply_style(
            doc,
            "Heading 1",
            font_fe="黑体",
            font_ascii="Times New Roman",
            size=16,
            bold=True,
            align=align_left,
            before=12,
            after=6,
            indent=0,
            spacing_rule=line_rule,
            keep_with_next=True,
        )
        _apply_style(
            doc,
            "标题 1",
            font_fe="黑体",
            font_ascii="Times New Roman",
            size=16,
            bold=True,
            align=align_left,
            before=12,
            after=6,
            indent=0,
            spacing_rule=line_rule,
            keep_with_next=True,
        )
        _apply_style(
            doc,
            "Heading 2",
            font_fe="黑体",
            font_ascii="Times New Roman",
            size=14,
            bold=True,
            align=align_left,
            before=6,
            after=6,
            indent=0,
            spacing_rule=line_rule,
            keep_with_next=True,
        )
        _apply_style(
            doc,
            "标题 2",
            font_fe="黑体",
            font_ascii="Times New Roman",
            size=14,
            bold=True,
            align=align_left,
            before=6,
            after=6,
            indent=0,
            spacing_rule=line_rule,
            keep_with_next=True,
        )
        _apply_style(
            doc,
            "Heading 3",
            font_fe="黑体",
            font_ascii="Times New Roman",
            size=12,
            bold=True,
            align=align_left,
            before=3,
            after=3,
            indent=0,
            spacing_rule=line_rule,
            keep_with_next=True,
        )
        _apply_style(
            doc,
            "标题 3",
            font_fe="黑体",
            font_ascii="Times New Roman",
            size=12,
            bold=True,
            align=align_left,
            before=3,
            after=3,
            indent=0,
            spacing_rule=line_rule,
            keep_with_next=True,
        )

        heading_prefix = __import__("re").compile(r"^\\s*\\d+(?:\\.\\d+)*[.、)]\\s*")
        for para in doc.Paragraphs:
            try:
                style = para.Range.Style
                style_name = str(getattr(style, "NameLocal", "") or getattr(style, "Name", ""))
            except Exception:
                style_name = ""
            if style_name not in {"Heading 1", "Heading 2", "Heading 3", "标题 1", "标题 2", "标题 3"}:
                continue
            text = (para.Range.Text or "").strip()
            if not text:
                continue
            new_text = heading_prefix.sub("", text)
            if new_text and new_text != text:
                rng = para.Range
                rng.End -= 1
                rng.Text = new_text

        _apply_multilevel_numbering(doc, constants, app)

        toc_position = (os.getenv("REPORT_TOC_POSITION", "before_outline") or "before_outline").strip().lower()
        if toc_position != "none":
            _ensure_toc(doc, constants, app, toc_position)

        try:
            doc.Fields.Update()
        except Exception:
            pass
        try:
            if doc.TablesOfContents.Count > 0:
                for idx in range(1, doc.TablesOfContents.Count + 1):
                    doc.TablesOfContents(idx).Update()
        except Exception:
            pass
        com_retry(lambda: doc.Save())
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
