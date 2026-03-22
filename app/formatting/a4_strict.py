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


def _apply_style(
    doc,
    name: str,
    *,
    font_fe: str,
    font_ascii: str,
    size: float,
    bold: bool,
    align,
    before: float,
    after: float,
    indent: float,
    spacing_rule,
    spacing=None,
    keep_with_next: bool = False,
) -> None:
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

    def _level(
        level: int,
        *,
        fmt: str,
        style: int,
        linked_style: str,
        number_pos_cm: float,
        text_pos_cm: float,
        reset_on_higher: int,
    ) -> None:
        try:
            lvl = template.ListLevels(level)
            lvl.NumberFormat = fmt
            lvl.TrailingCharacter = constants.wdTrailingTab
            lvl.NumberStyle = style
            lvl.NumberPosition = _cm_to_points(app, number_pos_cm)
            lvl.TextPosition = _cm_to_points(app, text_pos_cm)
            lvl.ResetOnHigher = reset_on_higher
            lvl.StartAt = 1
            lvl.LinkedStyle = linked_style
            lvl.Alignment = constants.wdListLevelAlignLeft
        except Exception:
            return

    # Level 1: 一、
    _level(
        1,
        fmt="%1、",
        style=getattr(constants, "wdListNumberStyleChineseCounting", 10),
        linked_style="Heading 1",
        number_pos_cm=0.0,
        text_pos_cm=0.9,
        reset_on_higher=0,
    )
    # Level 2: （一）
    _level(
        2,
        fmt="（%2）",
        style=getattr(constants, "wdListNumberStyleChineseCounting", 10),
        linked_style="Heading 2",
        number_pos_cm=0.9,
        text_pos_cm=1.6,
        reset_on_higher=1,
    )
    # Level 3: 1.
    _level(
        3,
        fmt="%3.",
        style=constants.wdListNumberStyleArabic,
        linked_style="Heading 3",
        number_pos_cm=1.6,
        text_pos_cm=2.2,
        reset_on_higher=2,
    )
    # Level 4: （1）
    _level(
        4,
        fmt="（%4）",
        style=constants.wdListNumberStyleArabic,
        linked_style="Heading 4",
        number_pos_cm=2.2,
        text_pos_cm=2.8,
        reset_on_higher=3,
    )
    # Level 5: 1）
    _level(
        5,
        fmt="%5）",
        style=constants.wdListNumberStyleArabic,
        linked_style="Heading 5",
        number_pos_cm=2.8,
        text_pos_cm=3.4,
        reset_on_higher=4,
    )

    def _link(style_name: str, level: int) -> None:
        try:
            doc.Styles(style_name).LinkToListTemplate(template, level=level)
        except Exception:
            return

    # Link both English + Chinese-localized names when present.
    for name in ("Heading 1", "标题 1"):
        _link(name, 1)
    for name in ("Heading 2", "标题 2"):
        _link(name, 2)
    for name in ("Heading 3", "标题 3"):
        _link(name, 3)
    for name in ("Heading 4", "标题 4"):
        _link(name, 4)
    for name in ("Heading 5", "标题 5"):
        _link(name, 5)


def _ensure_toc(doc, constants, position: str) -> None:
    # Keep behavior consistent with thesis_standard: update existing TOC; otherwise insert one.
    try:
        if doc.TablesOfContents.Count > 0:
            for idx in range(1, doc.TablesOfContents.Count + 1):
                doc.TablesOfContents(idx).Update()
            return
    except Exception:
        pass

    if position == "none":
        return

    try:
        if position == "after_title":
            first_para = doc.Paragraphs(1)
            insert_range = doc.Range(first_para.Range.End, first_para.Range.End)
        else:
            insert_range = doc.Range(0, 0)
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
            LowerHeadingLevel=5,
            IncludePageNumbers=True,
            RightAlignPageNumbers=True,
        )
    except Exception:
        return


def _format_caption_paragraphs(doc, constants) -> None:
    # Apply caption formatting to paragraphs starting with 图/表+编号.
    if constants is None:
        return
    try:
        total = doc.Paragraphs.Count
    except Exception:
        return
    for idx in range(1, total + 1):
        para = doc.Paragraphs(idx)
        rng = para.Range
        text = (rng.Text or "").strip()
        if not text:
            continue
        if not (text.startswith("图") or text.startswith("表")):
            continue
        # Rough match: 图1 / 表1 / 图 1
        if len(text) > 40:
            continue
        digits = any(ch.isdigit() for ch in text[:8])
        if not digits:
            continue
        try:
            para.Range.ParagraphFormat.Alignment = constants.wdAlignParagraphCenter
        except Exception:
            pass
        try:
            font = para.Range.Font
            font.NameFarEast = "宋体"
            font.NameAscii = "Times New Roman"
            font.Size = 12  # 小四
            font.Bold = False
        except Exception:
            pass
        try:
            pf = para.Range.ParagraphFormat
            pf.SpaceBefore = 0
            pf.SpaceAfter = 0
            pf.FirstLineIndent = 0
            pf.LineSpacingRule = getattr(constants, "wdLineSpaceSingle", 0)
        except Exception:
            pass


def apply_a4_strict_profile(docx_path: str, root_dir: str) -> None:
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
        constants = get_win32_constants(win32)
        app = com_retry(lambda: word.Application)
        ps = com_retry(lambda: doc.PageSetup)

        # Page setup: A4 + default margins (top/bottom 2.54cm; left/right 3.18cm).
        def _set_pagesetup(name: str, value) -> None:
            try:
                com_retry(lambda: setattr(ps, name, value))
            except Exception:
                pass

        _set_pagesetup("PaperSize", constants.wdPaperA4)
        _set_pagesetup("TopMargin", _cm_to_points(app, 2.54))
        _set_pagesetup("BottomMargin", _cm_to_points(app, 2.54))
        _set_pagesetup("LeftMargin", _cm_to_points(app, 3.18))
        _set_pagesetup("RightMargin", _cm_to_points(app, 3.18))

        # Line spacing rules.
        line_single = getattr(constants, "wdLineSpaceSingle", 0)
        line_multiple = getattr(constants, "wdLineSpaceMultiple", 5)
        align_left = constants.wdAlignParagraphLeft

        # Body: 宋体小四，1.25倍行距，段前0.5行（约6pt），段后0。
        _apply_style(
            doc,
            "Normal",
            font_fe="宋体",
            font_ascii="Times New Roman",
            size=12,
            bold=False,
            align=align_left,
            before=6,
            after=0,
            indent=0,
            spacing_rule=line_multiple,
            spacing=15,  # 12pt * 1.25
            keep_with_next=False,
        )

        # Total title: 宋体三号加粗，单倍行距，段前后自动（这里用0/0，Word默认会更接近自动）。
        _apply_style(
            doc,
            "Title",
            font_fe="宋体",
            font_ascii="Times New Roman",
            size=16,
            bold=True,
            align=constants.wdAlignParagraphCenter,
            before=0,
            after=0,
            indent=0,
            spacing_rule=line_single,
            keep_with_next=True,
        )

        # Headings: 1级 黑体小三；2级 黑体四；3级/4级/5级：宋体小四（但仍作为标题样式）
        _apply_style(
            doc,
            "Heading 1",
            font_fe="黑体",
            font_ascii="Times New Roman",
            size=15,
            bold=True,
            align=align_left,
            before=6,
            after=0,
            indent=0,
            spacing_rule=line_multiple,
            spacing=15,
            keep_with_next=True,
        )
        _apply_style(
            doc,
            "标题 1",
            font_fe="黑体",
            font_ascii="Times New Roman",
            size=15,
            bold=True,
            align=align_left,
            before=6,
            after=0,
            indent=0,
            spacing_rule=line_multiple,
            spacing=15,
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
            after=0,
            indent=0,
            spacing_rule=line_multiple,
            spacing=15,
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
            after=0,
            indent=0,
            spacing_rule=line_multiple,
            spacing=15,
            keep_with_next=True,
        )
        for name in ("Heading 3", "标题 3", "Heading 4", "标题 4", "Heading 5", "标题 5"):
            _apply_style(
                doc,
                name,
                font_fe="宋体",
                font_ascii="Times New Roman",
                size=12,
                bold=True,
                align=align_left,
                before=6,
                after=0,
                indent=0,
                spacing_rule=line_multiple,
                spacing=15,
                keep_with_next=True,
            )

        _apply_multilevel_numbering(doc, constants, app)

        toc_position = (os.getenv("REPORT_TOC_POSITION", "after_title") or "after_title").strip().lower()
        _ensure_toc(doc, constants, toc_position)

        _format_caption_paragraphs(doc, constants)

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
