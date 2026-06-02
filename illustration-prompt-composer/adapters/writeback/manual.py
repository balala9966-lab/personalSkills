"""Writeback "adapter" for non-writable sources: prints snippets for manual paste.

Used for:
  - yuque_public (no write API for non-owners)
  - text (no original document)
"""

from __future__ import annotations

from typing import Any


def can_handle(source_type: str) -> bool:
    return source_type in ("yuque_public", "text")


def write(mapping: dict[str, Any]) -> dict[str, Any]:
    snippets: list[dict[str, str]] = []
    for entry in mapping.get("mappings", []):
        if entry.get("status") != "ok":
            continue
        local_path = entry.get("local_path") or entry.get("absolute_path", "")
        url = entry.get("remote_url") or local_path
        alt = entry.get("alt_text") or entry.get("filename", "")
        snippets.append({
            "position": entry.get("position", ""),
            "markdown": f"![{alt}]({url})",
            "filename": entry.get("filename", ""),
        })
    return {
        "ok": True,
        "snippets": snippets,
        "note": "Paste each markdown snippet at the indicated position. The source document is not writable from this skill.",
    }
