from __future__ import annotations

import os
import re
from pathlib import Path

from app.formatting.profiles import default_zhengda_template_path
from app.tools.win32_utils import (
    com_retry,
    dispatch_word_application_with_pid,
    install_ole_message_filter,
    restore_ole_message_filter,
)


LIST_TEMPLATE_NAME = "正大杯_多级编号"
CAPTION_LABEL_FIGURE = "图"
CAPTION_LABEL_TABLE = "表"
CAPTION_LABEL_NOTE = "附注"
CAPTION_LABEL_EQUATION = "公式"


def _caption_label_names(app) -> set[str]:
    names: set[str] = set()
    try:
        labels = app.CaptionLabels
        for i in range(1, labels.Count + 1):
            try:
                name = labels(i).Name
            except Exception:
                continue
            if isinstance(name, str) and name:
                names.add(name)
    except Exception:
        return set()
    return names


def _resolve_caption_label(app, preferred: str, fallbacks: list[str]) -> str:
    names = _caption_label_names(app)
    if preferred in names:
        return preferred
    try:
        app.CaptionLabels.Add(preferred)
    except Exception:
        pass
    names = _caption_label_names(app)
    if preferred in names:
        return preferred
    for candidate in fallbacks:
        if candidate in names:
            return candidate
    return preferred


def _resolve_caption_labels(app) -> dict[str, str]:
    return {
        "figure": _resolve_caption_label(app, CAPTION_LABEL_FIGURE, ["Figure", "图形"]),
        "table": _resolve_caption_label(app, CAPTION_LABEL_TABLE, ["表格", "Table"]),
        "note": _resolve_caption_label(app, CAPTION_LABEL_NOTE, ["注", "Note"]),
        "equation": _resolve_caption_label(app, CAPTION_LABEL_EQUATION, ["Equation", "公式"]),
    }


def _require_win32() -> None:
    if os.name != "nt":
        raise RuntimeError("“正大杯报告格式”需要在 Windows 上使用 win32com（Word）。")
    try:
        import win32com.client  # type: ignore  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("缺少 pywin32：请先安装 `pywin32` 并确保本机已安装 Microsoft Word。") from exc


def _ensure_caption_labels(word) -> None:
    for label in (CAPTION_LABEL_FIGURE, CAPTION_LABEL_TABLE, CAPTION_LABEL_NOTE, CAPTION_LABEL_EQUATION):
        try:
            word.CaptionLabels(label)
        except Exception:
            try:
                word.CaptionLabels.Add(label)
            except Exception:
                pass


def _apply_page_setup(doc) -> None:
    wdPaperA4 = 7
    wdOrientPortrait = 0
    cm_to_pt = 28.346456692913385

    page = doc.PageSetup
    page.PaperSize = wdPaperA4
    page.Orientation = wdOrientPortrait
    page.TopMargin = 2.54 * cm_to_pt
    page.BottomMargin = 2.54 * cm_to_pt
    page.LeftMargin = 3.18 * cm_to_pt
    page.RightMargin = 3.18 * cm_to_pt


def _attach_template_and_update_styles(doc, template_path: Path) -> None:
    if not template_path.exists():
        raise RuntimeError(f"未找到模板文件：{template_path}")
    debug = os.getenv("FORMAT_PROFILE_DEBUG", "").strip().lower() in {"1", "true", "yes", "y", "on"}

    def _dbg(message: str) -> None:
        if debug:
            print(f"[zhengda_cup] {message}", flush=True)

    attach_template = os.getenv("ZHENGDA_ATTACH_TEMPLATE", "").strip().lower() in {"1", "true", "yes", "y", "on"}
    if not attach_template:
        _dbg("attach template: skipped (set ZHENGDA_ATTACH_TEMPLATE=1 to enable)")
        return

    _dbg("attach template: set AttachedTemplate")
    try:
        doc.AttachedTemplate = str(template_path)
        _dbg("attach template: AttachedTemplate set")
    except Exception as exc:  # noqa: BLE001
        _dbg(f"attach template: AttachedTemplate failed: {exc}")
    _dbg("attach template: set UpdateStylesOnOpen")
    try:
        doc.UpdateStylesOnOpen = True
        _dbg("attach template: UpdateStylesOnOpen set")
    except Exception as exc:  # noqa: BLE001
        _dbg(f"attach template: UpdateStylesOnOpen failed: {exc}")
    # NOTE: doc.UpdateStyles() may hang on some documents/environments (Word add-ins,
    # style conflicts, or modal prompts). Enable explicitly if needed.
    if os.getenv("ZHENGDA_UPDATE_STYLES", "").strip().lower() in {"1", "true", "yes", "y", "on"}:
        _dbg("attach template: UpdateStyles")
        try:
            doc.UpdateStyles()
        except Exception:
            pass


def _find_list_template(doc):
    try:
        for i in range(1, doc.ListTemplates.Count + 1):
            lt = doc.ListTemplates(i)
            if getattr(lt, "Name", "") == LIST_TEMPLATE_NAME or getattr(lt, "NameLocal", "") == LIST_TEMPLATE_NAME:
                return lt
    except Exception:
        pass
    try:
        attached = getattr(doc, "AttachedTemplate", None)
        if attached and hasattr(attached, "ListTemplates"):
            for i in range(1, attached.ListTemplates.Count + 1):
                lt = attached.ListTemplates(i)
                if getattr(lt, "Name", "") == LIST_TEMPLATE_NAME or getattr(lt, "NameLocal", "") == LIST_TEMPLATE_NAME:
                    return lt
    except Exception:
        pass
    return None


def _apply_multilevel_numbering(doc) -> None:
    list_template = _find_list_template(doc)
    if list_template is None:
        try:
            list_template = doc.Application.ListGalleries(3).ListTemplates(1)
        except Exception:
            return

    wdStyleHeading1 = -2
    wdStyleHeading2 = -3
    wdStyleHeading3 = -4
    wdStyleHeading4 = -5
    wdStyleHeading5 = -6
    style_to_level = {
        doc.Styles(wdStyleHeading1).NameLocal: 1,
        doc.Styles(wdStyleHeading2).NameLocal: 2,
        doc.Styles(wdStyleHeading3).NameLocal: 3,
        doc.Styles(wdStyleHeading4).NameLocal: 4,
        doc.Styles(wdStyleHeading5).NameLocal: 5,
    }

    wdListApplyToWholeList = 0
    wdWord10ListBehavior = 2
    first = True
    for para in doc.Paragraphs:
        try:
            style_name = para.Range.Style.NameLocal
        except Exception:
            continue
        level = style_to_level.get(style_name)
        if not level:
            continue
        try:
            para.Range.ListFormat.ApplyListTemplateWithLevel(
                list_template,
                ContinuePreviousList=not first,
                ApplyTo=wdListApplyToWholeList,
                DefaultListBehavior=wdWord10ListBehavior,
                Level=level,
            )
        except TypeError:
            try:
                para.Range.ListFormat.ApplyListTemplateWithLevel(
                    list_template,
                    ContinuePreviousList=not first,
                    ApplyTo=wdListApplyToWholeList,
                    DefaultListBehavior=wdWord10ListBehavior,
                )
            except Exception:
                pass
        except Exception:
            pass
        first = False


def _looks_like_caption(text: str, label: str) -> bool:
    text = (text or "").strip()
    if not text:
        return False
    return bool(re.match(rf"^{re.escape(label)}\\s*\\d+|^{re.escape(label)}\\d+", text))


def _insert_table_captions(doc, labels: dict[str, str]) -> None:
    wdCaptionPositionAbove = 0
    wdStyleCaption = -35

    for table in doc.Tables:
        prev_para = None
        try:
            prev_para = table.Range.Paragraphs(1).Previous()
        except Exception:
            prev_para = None

        has_caption = False
        if prev_para is not None:
            try:
                if prev_para.Range.Style == doc.Styles(wdStyleCaption):
                    has_caption = True
                else:
                    has_caption = _looks_like_caption(prev_para.Range.Text, CAPTION_LABEL_TABLE) or _looks_like_caption(
                        prev_para.Range.Text,
                        labels.get("table", CAPTION_LABEL_TABLE),
                    )
            except Exception:
                has_caption = False
        if has_caption:
            continue

        try:
            table.Range.InsertCaption(
                Label=labels.get("table", CAPTION_LABEL_TABLE),
                Title="  ",
                Position=wdCaptionPositionAbove,
            )
        except Exception:
            continue

        try:
            cap_para = table.Range.Paragraphs(1).Previous()
            if cap_para is not None:
                cap_para.Range.Style = doc.Styles(wdStyleCaption)
                cap_para.Range.ParagraphFormat.Alignment = 1
        except Exception:
            pass


def _has_adjacent_figure_caption(doc, rng, labels: dict[str, str]) -> bool:
    wdStyleCaption = -35
    for neighbor in ("Next", "Previous"):
        try:
            para = getattr(rng.Paragraphs(1), neighbor)()
            if para is None:
                continue
            if para.Range.Style == doc.Styles(wdStyleCaption):
                return True
            if _looks_like_caption(para.Range.Text, CAPTION_LABEL_FIGURE) or _looks_like_caption(
                para.Range.Text,
                labels.get("figure", CAPTION_LABEL_FIGURE),
            ):
                return True
        except Exception:
            continue
    return False


def _insert_figure_captions(doc, labels: dict[str, str]) -> None:
    wdCaptionPositionBelow = 1
    wdStyleCaption = -35

    try:
        inline_shapes = doc.InlineShapes
    except Exception:
        inline_shapes = None

    if inline_shapes is not None:
        for shp in inline_shapes:
            try:
                rng = shp.Range
            except Exception:
                continue
            if _has_adjacent_figure_caption(doc, rng, labels):
                continue
            try:
                rng.InsertCaption(
                    Label=labels.get("figure", CAPTION_LABEL_FIGURE),
                    Title="  ",
                    Position=wdCaptionPositionBelow,
                )
            except Exception:
                continue
            try:
                next_para = rng.Paragraphs(1).Next()
                if next_para is not None:
                    next_para.Range.Style = doc.Styles(wdStyleCaption)
                    next_para.Range.ParagraphFormat.Alignment = 1
            except Exception:
                pass

    try:
        shapes = doc.Shapes
    except Exception:
        shapes = None

    if shapes is not None:
        for shp in shapes:
            try:
                anchor = shp.Anchor
                rng = anchor.Duplicate
            except Exception:
                continue
            if _has_adjacent_figure_caption(doc, rng, labels):
                continue
            try:
                rng.InsertCaption(
                    Label=labels.get("figure", CAPTION_LABEL_FIGURE),
                    Title="  ",
                    Position=wdCaptionPositionBelow,
                )
            except Exception:
                continue
            try:
                next_para = rng.Paragraphs(1).Next()
                if next_para is not None:
                    next_para.Range.Style = doc.Styles(wdStyleCaption)
                    next_para.Range.ParagraphFormat.Alignment = 1
            except Exception:
                pass


def _apply_three_line_tables(doc) -> None:
    wdBorderTop = -1
    wdBorderLeft = -2
    wdBorderBottom = -3
    wdBorderRight = -4
    wdBorderHorizontal = -5
    wdBorderVertical = -6

    wdLineStyleNone = 0
    wdLineStyleSingle = 1
    wdLineWidth050pt = 4

    try:
        table_font_size = float(os.getenv("ZHENGDA_TABLE_FONT_SIZE", "12").strip() or "12")
    except Exception:
        table_font_size = 12.0

    for table in doc.Tables:
        try:
            borders = table.Borders
        except Exception:
            continue

        for border_id in (
            wdBorderTop,
            wdBorderLeft,
            wdBorderBottom,
            wdBorderRight,
            wdBorderHorizontal,
            wdBorderVertical,
        ):
            try:
                borders(border_id).LineStyle = wdLineStyleNone
            except Exception:
                pass

        try:
            top = borders(wdBorderTop)
            top.LineStyle = wdLineStyleSingle
            top.LineWidth = wdLineWidth050pt
        except Exception:
            pass
        try:
            bottom = borders(wdBorderBottom)
            bottom.LineStyle = wdLineStyleSingle
            bottom.LineWidth = wdLineWidth050pt
        except Exception:
            pass

        try:
            if table.Rows.Count >= 1:
                header_bottom = table.Rows(1).Range.Borders(wdBorderBottom)
                header_bottom.LineStyle = wdLineStyleSingle
                header_bottom.LineWidth = wdLineWidth050pt
        except Exception:
            pass

        try:
            rng = table.Range
            rng.Font.NameFarEast = "宋体"
            rng.Font.Name = "Times New Roman"
            rng.Font.Size = table_font_size
            rng.ParagraphFormat.LineSpacingRule = 0
            rng.ParagraphFormat.SpaceBefore = 0
            rng.ParagraphFormat.SpaceAfter = 0
        except Exception:
            pass


def _number_equations(doc, labels: dict[str, str]) -> None:
    wdFieldEmpty = -1
    wdAlignTabRight = 2
    wdTabLeaderSpaces = 0

    try:
        omaths = doc.OMaths
        count = omaths.Count
    except Exception:
        return
    if not count:
        return

    page = doc.PageSetup
    usable_width = page.PageWidth - page.LeftMargin - page.RightMargin
    right_pos = page.LeftMargin + usable_width

    for i in range(1, count + 1):
        try:
            om = omaths(i)
            para = om.Range.Paragraphs(1)
        except Exception:
            continue

        has_seq = False
        try:
            for f in para.Range.Fields:
                code = getattr(f, "Code", None)
                if code is not None and "SEQ" in str(code.Text):
                    has_seq = True
                    break
        except Exception:
            has_seq = False
        if has_seq:
            continue

        try:
            para.Range.ParagraphFormat.TabStops.Add(
                Position=right_pos,
                Alignment=wdAlignTabRight,
                Leader=wdTabLeaderSpaces,
            )
        except Exception:
            pass

        try:
            end_rng = para.Range
            end_rng.Collapse(0)
            end_rng.InsertAfter("\t（")
            end_rng.Collapse(0)
            doc.Fields.Add(end_rng, wdFieldEmpty, f"SEQ {labels.get('equation', CAPTION_LABEL_EQUATION)} \\* ARABIC")
            end_rng.Collapse(0)
            end_rng.InsertAfter("）")
        except Exception:
            continue


def apply_zhengda_cup_profile(*, docx_path: str, root_dir: str) -> None:
    _require_win32()
    template_path = default_zhengda_template_path(root_dir)
    debug = os.getenv("FORMAT_PROFILE_DEBUG", "").strip().lower() in {"1", "true", "yes", "y", "on"}

    def _dbg(message: str) -> None:
        if debug:
            print(f"[zhengda_cup] {message}", flush=True)

    try:
        import pythoncom  # type: ignore
        import win32com.client as win32  # type: ignore  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"win32com 初始化失败：{exc}") from exc

    word = None
    doc = None
    try:
        pythoncom.CoInitialize()
        old_filter, message_filter = install_ole_message_filter()

        _dbg("dispatch Word.Application")
        word, word_pid = com_retry(dispatch_word_application_with_pid)
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
        _dbg(f"word pid={word_pid}" if word_pid else "word pid unavailable")

        _ensure_caption_labels(word)
        doc_path = str(Path(docx_path).resolve())
        _dbg(f"open doc: {doc_path}")
        try:
            doc = com_retry(
                lambda: word.Documents.Open(
                    doc_path,
                    ConfirmConversions=False,
                    ReadOnly=False,
                    AddToRecentFiles=False,
                    Revert=False,
                    OpenAndRepair=True,
                    NoEncodingDialog=True,
                )
            )
        except TypeError:
            doc = com_retry(lambda: word.Documents.Open(doc_path, ReadOnly=False))
        _dbg("doc opened")
        _dbg("resolve caption labels")
        labels = _resolve_caption_labels(doc.Application)

        _dbg("apply page setup")
        _apply_page_setup(doc)
        _dbg(f"attach template: {template_path}")
        _attach_template_and_update_styles(doc, template_path)
        _dbg("apply multilevel numbering")
        _apply_multilevel_numbering(doc)
        _dbg("insert table captions")
        _insert_table_captions(doc, labels)
        _dbg("insert figure captions")
        _insert_figure_captions(doc, labels)
        _dbg("apply three-line tables")
        _apply_three_line_tables(doc)
        _dbg("number equations")
        _number_equations(doc, labels)

        _dbg("update fields")
        try:
            doc.Fields.Update()
        except Exception:
            pass

        _dbg("save doc")
        com_retry(lambda: doc.Save())
        _dbg("done")
    finally:
        try:
            if doc is not None:
                com_retry(lambda: doc.Close(False), timeout_s=5.0)
        except Exception:
            pass
        try:
            if word is not None:
                com_retry(lambda: word.Quit(), timeout_s=5.0)
        except Exception:
            pass
        try:
            if message_filter is not None:
                restore_ole_message_filter(old_filter)
        except Exception:
            pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
