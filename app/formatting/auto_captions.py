from __future__ import annotations

import re
from pathlib import Path

from app.tools.win32_utils import (
    com_retry,
    dispatch_word_application_with_pid,
    install_ole_message_filter,
    restore_ole_message_filter,
)


_CAPTION_PATTERN = re.compile(r"^(图|表)\s*\d+")
_WD_MAIN_TEXT_STORY = 1
_WD_WITHIN_TABLE = 12
_WD_CAPTION_POS_ABOVE = 0
_WD_CAPTION_POS_BELOW = 1


def apply_auto_captions(
    *,
    docx_path: str,
    include_chapter_number: bool = True,
    chapter_style_level: int = 1,
    logger=None,
) -> None:
    path = str(Path(docx_path).resolve())

    def _log(message: str) -> None:
        if logger:
            logger(message)

    try:
        import pythoncom  # type: ignore
        import win32com.client as win32  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"win32com 初始化失败：{exc}") from exc

    def _ensure_label(doc, label: str):
        try:
            obj = doc.CaptionLabels(label)
        except Exception:
            try:
                obj = doc.CaptionLabels.Add(label)
            except Exception:
                obj = None
        if obj is None:
            return None
        if not include_chapter_number:
            return obj
        try:
            obj.IncludeChapterNumber = True
        except Exception:
            pass
        try:
            obj.ChapterStyleLevel = int(max(1, chapter_style_level))
        except Exception:
            pass
        return obj

    def _is_caption_text(text: str) -> bool:
        return bool(_CAPTION_PATTERN.match((text or "").strip()))

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
                    path,
                    ConfirmConversions=False,
                    ReadOnly=False,
                    AddToRecentFiles=False,
                    Revert=False,
                    OpenAndRepair=True,
                    NoEncodingDialog=True,
                )
            )
        except TypeError:
            doc = com_retry(lambda: word.Documents.Open(path))
        _ensure_label(doc, "图")
        _ensure_label(doc, "表")

        main = doc.StoryRanges(_WD_MAIN_TEXT_STORY)
        paras = main.Paragraphs
        total = paras.Count

        inserted_fig = 0
        inserted_tbl = 0

        # Insert from end to start to keep indices stable.
        for idx in range(total, 0, -1):
            para = paras(idx)
            rng = para.Range
            text = (rng.Text or "").strip()

            try:
                in_table = bool(rng.Information(_WD_WITHIN_TABLE))
            except Exception:
                in_table = False
            if in_table:
                continue

            # Table captions (above).
            try:
                table_count = int(getattr(rng.Tables, "Count", 0) or 0)
            except Exception:
                table_count = 0
            if table_count > 0:
                prev_text = ""
                try:
                    if idx > 1:
                        prev_text = (paras(idx - 1).Range.Text or "").strip()
                except Exception:
                    prev_text = ""
                if prev_text and _is_caption_text(prev_text):
                    continue
                try:
                    rng.InsertCaption(
                        Label="表",
                        Title=" ",
                        Position=_WD_CAPTION_POS_ABOVE,
                        ExcludeLabel=0,
                    )
                    inserted_tbl += 1
                except Exception:
                    continue
                continue

            # Figure captions (below) for inline shapes.
            try:
                shape_count = int(getattr(rng.InlineShapes, "Count", 0) or 0)
            except Exception:
                shape_count = 0
            if shape_count <= 0:
                continue

            next_text = ""
            try:
                if idx < total:
                    next_text = (paras(idx + 1).Range.Text or "").strip()
            except Exception:
                next_text = ""
            if next_text and _is_caption_text(next_text):
                continue

            try:
                rng.InsertCaption(
                    Label="图",
                    Title=" ",
                    Position=_WD_CAPTION_POS_BELOW,
                    ExcludeLabel=0,
                )
                inserted_fig += 1
            except Exception:
                continue

        try:
            doc.Fields.Update()
        except Exception:
            pass
        try:
            if doc.TablesOfContents.Count > 0:
                for i in range(1, doc.TablesOfContents.Count + 1):
                    doc.TablesOfContents(i).Update()
        except Exception:
            pass
        com_retry(lambda: doc.Save())
        _log(f"[captions] inserted figures={inserted_fig} tables={inserted_tbl}")
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
