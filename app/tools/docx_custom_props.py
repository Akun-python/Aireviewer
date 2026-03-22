from __future__ import annotations

import io
import os
import tempfile
import uuid
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET


_DOCX_LIKE_SUFFIXES = {".docx", ".docm", ".dotx", ".dotm"}

_CUSTOM_NS = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
_VT_NS = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

_CUSTOM_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties"
_CUSTOM_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.custom-properties+xml"
_CUSTOM_FMTID = "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}"


def _xml_bytes(root: ET.Element) -> bytes:
    buff = io.BytesIO()
    ET.ElementTree(root).write(buff, encoding="utf-8", xml_declaration=True)
    return buff.getvalue()


def read_custom_prop(docx_path: str | Path, name: str) -> str | None:
    path = Path(docx_path)
    if path.suffix.lower() not in _DOCX_LIKE_SUFFIXES or not path.exists():
        return None
    if not name:
        return None

    try:
        with zipfile.ZipFile(path, "r") as archive:
            try:
                xml_bytes = archive.read("docProps/custom.xml")
            except Exception:
                return None
    except Exception:
        return None

    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return None

    for prop in root.findall(f".//{{{_CUSTOM_NS}}}property"):
        if (prop.attrib.get("name") or "") != name:
            continue
        for child in list(prop):
            text = (child.text or "").strip()
            if text:
                return text
        return None
    return None


def ensure_custom_prop(docx_path: str | Path, name: str, *, value: str | None = None) -> str | None:
    path = Path(docx_path)
    if path.suffix.lower() not in _DOCX_LIKE_SUFFIXES or not path.exists():
        return None
    if not name:
        return None
    existing = read_custom_prop(path, name)
    if existing:
        return existing
    resolved = (value or "").strip() or uuid.uuid4().hex
    ok = set_custom_prop(path, name, resolved)
    return resolved if ok else None


def set_custom_prop(docx_path: str | Path, name: str, value: str) -> bool:
    path = Path(docx_path)
    if path.suffix.lower() not in _DOCX_LIKE_SUFFIXES or not path.exists():
        return False
    if not name:
        return False
    try:
        return _set_custom_prop_zip(path, name, value)
    except Exception:
        return False


def _update_custom_xml(existing: bytes | None, name: str, value: str) -> bytes:
    ET.register_namespace("", _CUSTOM_NS)
    ET.register_namespace("vt", _VT_NS)

    root = None
    if existing:
        try:
            root = ET.fromstring(existing)
        except Exception:
            root = None
    if root is None or root.tag != f"{{{_CUSTOM_NS}}}Properties":
        root = ET.Element(f"{{{_CUSTOM_NS}}}Properties")

    props = root.findall(f".//{{{_CUSTOM_NS}}}property")
    target = next((p for p in props if (p.attrib.get("name") or "") == name), None)
    if target is None:
        max_pid = 1
        for p in props:
            try:
                pid = int(p.attrib.get("pid", 0) or 0)
            except Exception:
                pid = 0
            max_pid = max(max_pid, pid)
        new_pid = max(2, max_pid + 1)
        target = ET.SubElement(
            root,
            f"{{{_CUSTOM_NS}}}property",
            {"fmtid": _CUSTOM_FMTID, "pid": str(new_pid), "name": name},
        )
    else:
        for child in list(target):
            target.remove(child)
        target.attrib.setdefault("fmtid", _CUSTOM_FMTID)
        if not target.attrib.get("pid"):
            target.attrib["pid"] = "2"

    elem = ET.SubElement(target, f"{{{_VT_NS}}}lpwstr")
    elem.text = value or ""
    return _xml_bytes(root)


def _ensure_content_types(xml_bytes: bytes) -> bytes:
    ET.register_namespace("", _CT_NS)
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return xml_bytes
    if root.tag != f"{{{_CT_NS}}}Types":
        return xml_bytes
    for override in root.findall(f".//{{{_CT_NS}}}Override"):
        if (override.attrib.get("PartName") or "") == "/docProps/custom.xml":
            override.attrib.setdefault("ContentType", _CUSTOM_CONTENT_TYPE)
            return _xml_bytes(root)
    ET.SubElement(
        root,
        f"{{{_CT_NS}}}Override",
        {"PartName": "/docProps/custom.xml", "ContentType": _CUSTOM_CONTENT_TYPE},
    )
    return _xml_bytes(root)


def _ensure_root_rels(xml_bytes: bytes) -> bytes:
    ET.register_namespace("", _REL_NS)
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return xml_bytes
    if root.tag != f"{{{_REL_NS}}}Relationships":
        return xml_bytes

    rels = root.findall(f".//{{{_REL_NS}}}Relationship")
    for rel in rels:
        if (rel.attrib.get("Type") or "") == _CUSTOM_REL_TYPE:
            rel.attrib["Target"] = "docProps/custom.xml"
            return _xml_bytes(root)

    max_id = 0
    for rel in rels:
        rid = rel.attrib.get("Id") or ""
        if rid.lower().startswith("rid"):
            try:
                max_id = max(max_id, int(rid[3:]))
            except Exception:
                continue
    new_id = f"rId{max_id + 1 if max_id else (len(rels) + 1)}"
    ET.SubElement(
        root,
        f"{{{_REL_NS}}}Relationship",
        {"Id": new_id, "Type": _CUSTOM_REL_TYPE, "Target": "docProps/custom.xml"},
    )
    return _xml_bytes(root)


def _set_custom_prop_zip(path: Path, name: str, value: str) -> bool:
    fd, tmp_name = tempfile.mkstemp(prefix=path.stem + "_props_", suffix=path.suffix, dir=str(path.parent))
    os.close(fd)
    tmp_path = Path(tmp_name)

    try:
        with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(tmp_path, "w") as zout:
            names = set(zin.namelist())
            existing_custom = None
            if "docProps/custom.xml" in names:
                try:
                    existing_custom = zin.read("docProps/custom.xml")
                except Exception:
                    existing_custom = None
            updated_custom = _update_custom_xml(existing_custom, name, value)
            wrote_custom = False
            wrote_ct = False
            wrote_root_rels = False

            for info in zin.infolist():
                filename = info.filename
                data = zin.read(filename)
                if filename == "docProps/custom.xml":
                    data = updated_custom
                    wrote_custom = True
                elif filename == "[Content_Types].xml":
                    data = _ensure_content_types(data)
                    wrote_ct = True
                elif filename == "_rels/.rels":
                    data = _ensure_root_rels(data)
                    wrote_root_rels = True
                zout.writestr(info, data)

            if not wrote_custom:
                zout.writestr("docProps/custom.xml", updated_custom)
            if not wrote_ct and "[Content_Types].xml" in names:
                # Should not happen; still keep safe.
                pass
            if not wrote_root_rels and "_rels/.rels" in names:
                pass

        tmp_path.replace(path)
        return True
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
