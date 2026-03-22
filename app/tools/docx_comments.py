from __future__ import annotations

import os
from pathlib import Path
import re
import stat
import tempfile
import zipfile

from app.tools.win32_utils import (
    com_retry,
    dispatch_word_application,
    install_ole_message_filter,
    restore_ole_message_filter,
)

_COMMENT_MARKER_PATTERN = re.compile(
    br"("  # comment range markers
    br"<(?:[A-Za-z0-9_]+:)?commentRangeStart\b[^>]*/\s*>"
    br"|<(?:[A-Za-z0-9_]+:)?commentRangeStart\b[^>]*>.*?</(?:[A-Za-z0-9_]+:)?commentRangeStart\s*>"
    br"|<(?:[A-Za-z0-9_]+:)?commentRangeEnd\b[^>]*/\s*>"
    br"|<(?:[A-Za-z0-9_]+:)?commentRangeEnd\b[^>]*>.*?</(?:[A-Za-z0-9_]+:)?commentRangeEnd\s*>"
    br"|<(?:[A-Za-z0-9_]+:)?commentReference\b[^>]*/\s*>"
    br"|<(?:[A-Za-z0-9_]+:)?commentReference\b[^>]*>.*?</(?:[A-Za-z0-9_]+:)?commentReference\s*>"
    br")",
    flags=re.IGNORECASE | re.DOTALL,
)
_REL_COMMENT_PATTERN = re.compile(
    br"<Relationship\b[^>]*\bType=['\"][^'\"]*comments[^'\"]*['\"][^>]*/\s*>",
    flags=re.IGNORECASE,
)
_CT_COMMENT_PATTERN = re.compile(
    br"<Override\b[^>]*\bPartName=['\"]/word/comments[^'\"]*['\"][^>]*/\s*>",
    flags=re.IGNORECASE,
)


def _has_win32() -> bool:
    if os.name != "nt":
        return False
    try:
        import win32com.client  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def _ensure_writable(path: Path) -> None:
    try:
        os.chmod(path, os.stat(path).st_mode | stat.S_IWRITE)
    except Exception:
        return


def _strip_comment_markers(xml_bytes: bytes) -> bytes:
    try:
        return _COMMENT_MARKER_PATTERN.sub(b"", xml_bytes)
    except Exception:
        return xml_bytes


def _strip_comment_relationships(xml_bytes: bytes) -> bytes:
    try:
        return _REL_COMMENT_PATTERN.sub(b"", xml_bytes)
    except Exception:
        return xml_bytes


def _strip_comment_content_types(xml_bytes: bytes) -> bytes:
    try:
        return _CT_COMMENT_PATTERN.sub(b"", xml_bytes)
    except Exception:
        return xml_bytes


def strip_docx_comments(docx_path: str | Path, *, prefer_win32: bool = False) -> bool:
    """
    Remove existing Word comments from a docx-like file in-place (.docx/.docm/.dotx/.dotm).

    Returns True when a best-effort removal was attempted and the file was rewritten.
    """
    path = Path(docx_path)
    if path.suffix.lower() not in {".docx", ".docm", ".dotx", ".dotm"} or not path.exists():
        return False

    _ensure_writable(path)
    if prefer_win32 and _has_win32():
        try:
            return _strip_docx_comments_win32(path)
        except Exception:
            pass

    try:
        return _strip_docx_comments_zip(path)
    except Exception:
        return False


def _strip_docx_comments_win32(path: Path) -> bool:
    try:
        import pythoncom  # type: ignore
        import win32com.client as win32  # type: ignore
    except Exception:
        return False

    pythoncom.CoInitialize()
    old_filter, message_filter = install_ole_message_filter()
    word = None
    doc = None
    try:
        word = com_retry(dispatch_word_application)
        word.Visible = False
        word.DisplayAlerts = 0
        doc = com_retry(lambda: word.Documents.Open(str(path)))
        try:
            count = int(doc.Comments.Count)
        except Exception:
            count = 0
        if count <= 0:
            return False
        for idx in range(count, 0, -1):
            try:
                doc.Comments(idx).Delete()
            except Exception:
                continue
        com_retry(lambda: doc.Save())
        return True
    finally:
        try:
            if doc is not None:
                try:
                    com_retry(lambda: doc.Close(SaveChanges=False), timeout_s=5.0)
                except Exception:
                    pass
        finally:
            if word is not None:
                try:
                    com_retry(lambda: word.Quit(), timeout_s=5.0)
                except Exception:
                    pass
            if message_filter is not None:
                restore_ole_message_filter(old_filter)
            pythoncom.CoUninitialize()


def _strip_docx_comments_zip(path: Path) -> bool:
    fd, tmp_name = tempfile.mkstemp(prefix=path.stem + "_nocomments_", suffix=".docx", dir=str(path.parent))
    os.close(fd)
    tmp_path = Path(tmp_name)

    try:
        with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(tmp_path, "w") as zout:
            names = set(zin.namelist())
            comment_parts = [
                name for name in names if name.startswith("word/comments") and name.lower().endswith(".xml")
            ]
            needs_processing = bool(comment_parts)
            if not needs_processing:
                candidate = "word/document.xml"
                if candidate in names:
                    try:
                        data = zin.read(candidate)
                        needs_processing = b"commentRangeStart" in data or b"commentReference" in data
                    except Exception:
                        needs_processing = False
                if not needs_processing:
                    rels = "word/_rels/document.xml.rels"
                    if rels in names:
                        try:
                            needs_processing = b"comments" in zin.read(rels).lower()
                        except Exception:
                            needs_processing = False

            if not needs_processing:
                return False

            for info in zin.infolist():
                name = info.filename
                data = zin.read(name)
                if name.startswith("word/comments") and name.lower().endswith(".xml"):
                    continue
                if name == "[Content_Types].xml":
                    data = _strip_comment_content_types(data)
                elif name.startswith("word/_rels/") and name.lower().endswith(".rels"):
                    data = _strip_comment_relationships(data)
                elif name.startswith("word/") and name.lower().endswith(".xml"):
                    data = _strip_comment_markers(data)
                zout.writestr(info, data)

        tmp_path.replace(path)
        return True
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
