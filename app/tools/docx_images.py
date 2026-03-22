from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from app.tools.path_utils import ensure_parent, ensure_workspace_dir, resolve_path, to_virtual_path


_DOCX_LIKE_SUFFIXES = {".docx", ".docm", ".dotx", ".dotm"}


def _is_docx_like(path: Path) -> bool:
    return path.suffix.lower() in _DOCX_LIKE_SUFFIXES


def _normalize_engine(engine: str | None) -> str:
    value = (engine or "").strip().lower()
    if not value or value == "auto":
        return "auto"
    if value in {"zip", "zipfile", "package"}:
        return "zipfile"
    if value in {"win32", "win32com", "com", "word"}:
        return "win32com"
    raise ValueError(f"Unknown image extraction engine: {engine}")


def _can_import_win32() -> bool:
    if os.name != "nt":
        return False
    try:
        import pythoncom  # type: ignore  # noqa: F401
        import win32com.client  # type: ignore  # noqa: F401

        return True
    except Exception:
        return False


def _extract_images_zipfile(input_real: Path, images_real: Path) -> tuple[list[dict[str, Any]], list[str]]:
    images: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        with zipfile.ZipFile(str(input_real), "r") as archive:
            members = [name for name in archive.namelist() if name.startswith("word/media/") and not name.endswith("/")]
            for idx, name in enumerate(sorted(members), start=1):
                try:
                    data = archive.read(name)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"read {name}: {exc}")
                    continue
                filename = Path(name).name or f"image_{idx:04d}.bin"
                target = images_real / filename
                if target.exists():
                    target = images_real / f"{target.stem}_{idx:04d}{target.suffix}"
                try:
                    target.write_bytes(data)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"write {target}: {exc}")
                    continue
                images.append(
                    {
                        "index": idx,
                        "kind": "package",
                        "zip_path": name,
                        "filename": target.name,
                        "path": str(target),
                        "virtual_path": to_virtual_path(target),
                        "bytes": len(data),
                    }
                )
    except zipfile.BadZipFile as exc:
        errors.append(f"bad docx(zip): {exc}")
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))
    return images, errors


def _sha1_file(path: Path) -> str:
    hasher = hashlib.sha1()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _dedupe_images_by_sha1(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Compute sha1 for image files and drop duplicates from `secondary`.

    Returns: (primary_with_sha1, filtered_secondary_with_sha1)
    """

    seen: set[str] = set()
    primary_out: list[dict[str, Any]] = []
    for item in primary:
        path = item.get("path")
        if not isinstance(path, str) or not path:
            primary_out.append(item)
            continue
        try:
            digest = _sha1_file(Path(path))
        except Exception:
            primary_out.append(item)
            continue
        item = dict(item)
        item.setdefault("sha1", digest)
        primary_out.append(item)
        seen.add(digest)

    secondary_out: list[dict[str, Any]] = []
    for item in secondary:
        path = item.get("path")
        if not isinstance(path, str) or not path:
            secondary_out.append(item)
            continue
        file_path = Path(path)
        try:
            digest = _sha1_file(file_path)
        except Exception:
            secondary_out.append(item)
            continue
        if digest in seen:
            try:
                file_path.unlink()
            except Exception:
                pass
            continue
        item = dict(item)
        item.setdefault("sha1", digest)
        secondary_out.append(item)
        seen.add(digest)

    return primary_out, secondary_out


def _renumber_images(images: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, item in enumerate(images, start=1):
        updated = dict(item)
        updated["index"] = idx
        out.append(updated)
    return out


def _extract_images_win32com(input_real: Path, images_real: Path) -> tuple[list[dict[str, Any]], list[str]]:
    images: list[dict[str, Any]] = []
    errors: list[str] = []
    if not _can_import_win32():
        return images, ["win32com is not available (pywin32 not installed or not Windows)"]

    from app.tools.win32_utils import com_retry, dispatch_word_application, win32com_context

    with win32com_context():
        import win32com.client as win32  # type: ignore

        word = None
        doc = None
        tmp_dir: Path | None = None
        keep_exports = os.getenv("KEEP_WORD_EXPORTS", "").strip().lower() in {"1", "true", "yes", "y", "on"}
        try:
            word = com_retry(dispatch_word_application)
            word.Visible = False
            word.DisplayAlerts = 0
            try:
                word.AutomationSecurity = 3  # msoAutomationSecurityForceDisable
            except Exception:
                pass
            try:
                word.Options.UpdateLinksAtOpen = False
            except Exception:
                pass
            doc = com_retry(
                lambda: word.Documents.Open(
                    str(input_real),
                    ConfirmConversions=False,
                    ReadOnly=True,
                    AddToRecentFiles=False,
                )
            )
            # Word's COM model doesn't reliably support Shape/InlineShape.SaveAsPicture across versions.
            # Instead, render the document to HTML and collect exported images.
            tmp_root = ensure_workspace_dir() / "tmp_word_exports"
            tmp_root.mkdir(parents=True, exist_ok=True)
            tmp_dir = Path(tempfile.mkdtemp(prefix="docx_images_", dir=str(tmp_root)))
            html_path = (tmp_dir / f"{input_real.stem}.html").resolve()
            # wdFormatFilteredHTML = 10
            com_retry(lambda: doc.SaveAs2(str(html_path), FileFormat=10))

            assets_candidates = [
                html_path.with_suffix(".files"),
                html_path.with_name(f"{html_path.stem}_files"),
            ]
            assets_dir = next((p for p in assets_candidates if p.is_dir()), None)
            if assets_dir is None:
                # Fallback: pick the first directory under tmp_dir that looks like an assets folder.
                try:
                    dirs = [p for p in tmp_dir.iterdir() if p.is_dir()]
                except Exception:
                    dirs = []
                assets_dir = next((p for p in dirs if p.name.lower().startswith(html_path.stem.lower())), None)

            if assets_dir is None or not assets_dir.exists():
                errors.append("win32com html export produced no assets directory")
            else:
                try:
                    exported_files = sorted([p for p in assets_dir.iterdir() if p.is_file()], key=lambda p: p.name)
                except Exception:
                    exported_files = []
                image_exts = {
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                    ".bmp",
                    ".tif",
                    ".tiff",
                    ".wmf",
                    ".emf",
                    ".emz",
                    ".wmz",
                    ".svg",
                    ".webp",
                }
                exported = 0
                for src in exported_files:
                    if src.suffix.lower() not in image_exts:
                        continue
                    exported += 1
                    dest = images_real / src.name
                    if dest.exists():
                        dest = images_real / f"{dest.stem}_{exported:04d}{dest.suffix}"
                    try:
                        shutil.copy2(src, dest)
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"copy {src.name}: {exc}")
                        continue
                    try:
                        size = int(dest.stat().st_size)
                    except Exception:
                        size = 0
                    if size <= 0:
                        continue
                    images.append(
                        {
                            "index": int(len(images) + 1),
                            "kind": "win32_html",
                            "filename": dest.name,
                            "path": str(dest),
                            "virtual_path": to_virtual_path(dest),
                            "bytes": size,
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
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
            if tmp_dir is not None and not keep_exports:
                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass

    return images, errors


def extract_docx_images(
    input_path: str,
    *,
    output_path: str | None = None,
    images_dir: str | None = None,
    engine: str | None = None,
) -> str:
    """
    Extract images from a Word file.

    Engine:
      - auto (default): extract `word/media/*` via zipfile, and also export rendered images (shapes/charts) via Word when available
      - zipfile: unzip `word/media/*` and dump raw bytes
      - win32com: export InlineShapes/Shapes via Microsoft Word automation

    Returns a virtual path to the JSON output.
    """

    input_real = resolve_path(input_path)
    requested_engine = _normalize_engine(engine)
    if requested_engine in {"auto", "zipfile"} and not _is_docx_like(input_real):
        if requested_engine == "zipfile":
            raise ValueError("zipfile image extraction requires a docx-like package (.docx/.docm/.dotx/.dotm)")
        requested_engine = "win32com"

    if output_path:
        output_real = resolve_path(output_path)
    else:
        output_real = input_real.with_suffix(".images.json")
    ensure_parent(output_real)

    workspace = ensure_workspace_dir()
    if images_dir:
        images_real = resolve_path(images_dir)
    else:
        images_real = workspace / "doc_images" / input_real.stem / dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    images_real.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "document": str(input_real.name),
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "engine": requested_engine,
        "images_dir": str(images_real),
        "virtual_images_dir": to_virtual_path(images_real),
        "images": [],
        "errors": [],
        "warnings": [],
    }

    if requested_engine == "zipfile":
        images, errors = _extract_images_zipfile(input_real, images_real)
        payload["images"] = images
        payload["errors"] = errors
    elif requested_engine == "win32com":
        images, errors = _extract_images_win32com(input_real, images_real)
        payload["images"] = images
        payload["errors"] = errors
    else:
        # auto
        if _is_docx_like(input_real):
            images, errors = _extract_images_zipfile(input_real, images_real)
            payload["engine"] = "zipfile"
            payload["images"] = images
            payload["errors"] = errors

            # When Word automation is available, also export "rendered" images via HTML:
            # charts, shapes, SmartArt, etc. (Some of these do not live in word/media.)
            if _can_import_win32():
                win32_images, win32_errors = _extract_images_win32com(input_real, images_real)
                if win32_images:
                    images_with_hash, win32_with_hash = _dedupe_images_by_sha1(images, win32_images)
                    payload["images"] = images_with_hash + win32_with_hash
                    payload["engine"] = "zipfile+win32com"
                if win32_errors:
                    if images:
                        payload["warnings"].extend([f"win32com export failed: {err}" for err in win32_errors])
                    else:
                        payload["errors"] = errors + win32_errors
                if not images and win32_images:
                    payload["engine"] = "win32com"
                if not images:
                    payload["warnings"].append("no images found in word/media; attempted win32com export")
                elif win32_images:
                    payload["warnings"].append("added rendered images via win32com html export")
        else:
            images, errors = _extract_images_win32com(input_real, images_real)
            payload["engine"] = "win32com"
            payload["images"] = images
            payload["errors"] = errors

    if isinstance(payload.get("images"), list):
        payload["images"] = _renumber_images(payload["images"])
    output_real.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return to_virtual_path(output_real)
