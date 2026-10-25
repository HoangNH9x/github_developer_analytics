from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

PBIX = Path("Ass_final.pbix")

def try_json(raw: Any):
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return {}

def deep_strings(obj: Any, out: list[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.casefold() in {"queryref", "displayname", "property", "entity", "measure", "column", "name"} and isinstance(v, str):
                if len(v) < 160:
                    out.append(v)
            deep_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            deep_strings(v, out)

def summarize_pbix(path: Path) -> dict:
    result: dict[str, Any] = {
        "file": path.name,
        "file_size_bytes": path.stat().st_size,
        "is_zip_container": zipfile.is_zipfile(path),
        "archive_entries": [],
        "pages": [],
        "model_metadata_files": [],
    }
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        result["archive_entries"] = names[:80]
        result["model_metadata_files"] = [
            n for n in names
            if any(k in n.casefold() for k in ("model", "diagram", "schema", "connection", "metadata"))
        ][:60]
        layout_name = next((n for n in names if n.casefold() in {"report/layout", "report/layout.json"}), None)
        if not layout_name:
            result["layout_found"] = False
            return result
        result["layout_found"] = True
        raw_layout = zf.read(layout_name)
        if raw_layout[:2] == bytes([0xff, 0xfe]) or raw_layout[:2] == bytes([0xfe, 0xff]):
            decoded_layout = raw_layout.decode("utf-16")
        elif len(raw_layout) > 1 and raw_layout[0] == ord("{") and raw_layout[1] == 0:
            decoded_layout = raw_layout.decode("utf-16-le")
        else:
            try:
                decoded_layout = raw_layout.decode("utf-8-sig")
            except UnicodeDecodeError:
                decoded_layout = raw_layout.decode("cp1252")
        try:
            layout = json.loads(decoded_layout.lstrip(chr(0xfeff) + chr(0x00) + chr(0x200b)))
        except Exception as exc:
            print("LAYOUT_DIAGNOSTIC", json.dumps({
                "member": layout_name,
                "raw_length": len(raw_layout),
                "raw_hex": raw_layout[:48].hex(),
                "raw_repr": repr(raw_layout[:48]),
                "utf8_repr": repr(raw_layout[:80].decode("utf-8", errors="replace")),
                "utf16le_repr": repr(raw_layout[:80].decode("utf-16-le", errors="replace")),
                "utf16be_repr": repr(raw_layout[:80].decode("utf-16-be", errors="replace")),
                "decoded_prefix": repr(decoded_layout[:100]),
                "error": str(exc),
            }, ensure_ascii=False))
            raise
        sections = layout.get("sections", [])
        for index, sec in enumerate(sections, start=1):
            page = {
                "page_index": index,
                "display_name": sec.get("displayName") or sec.get("name") or f"Page {index}",
                "page_name": sec.get("name"),
                "visual_count": 0,
                "visual_types": [],
                "visuals": [],
            }
            visuals = sec.get("visualContainers", [])
            page["visual_count"] = len(visuals)
            types = []
            for visual_index, vc in enumerate(visuals, start=1):
                config = try_json(vc.get("config"))
                query = try_json(vc.get("query"))
                transform = try_json(vc.get("dataTransforms"))
                single = config.get("singleVisual", {}) if isinstance(config, dict) else {}
                vtype = single.get("visualType") or config.get("visualType") or "unknown"
                title = ""
                objects = single.get("objects", {}) if isinstance(single, dict) else {}
                title_objects = objects.get("title", []) if isinstance(objects, dict) else []
                for item in title_objects if isinstance(title_objects, list) else []:
                    props = item.get("properties", {})
                    text_node = props.get("text", {})
                    literal = text_node.get("expr", {}).get("Literal", {}).get("Value")
                    if isinstance(literal, str):
                        title = literal.strip("'")
                        break
                field_names = []
                deep_strings(query, field_names)
                deep_strings(transform, field_names)
                # Preserve order while keeping the list compact and readable.
                cleaned = []
                for value in field_names:
                    value = str(value).strip()
                    if value and value not in cleaned and not value.startswith("http"):
                        cleaned.append(value)
                page["visuals"].append({
                    "visual_index": visual_index,
                    "visual_type": vtype,
                    "title": title,
                    "field_or_query_labels": cleaned[:20],
                })
                types.append(vtype)
            page["visual_types"] = sorted(set(types))
            result["pages"].append(page)
        result["page_count"] = len(result["pages"])
        result["report_layout_keys"] = list(layout.keys())
        return result

if __name__ == "__main__":
    if not PBIX.exists():
        raise SystemExit("Ass_final.pbix not found in repository root.")
    print(json.dumps(summarize_pbix(PBIX), ensure_ascii=False, indent=2))
