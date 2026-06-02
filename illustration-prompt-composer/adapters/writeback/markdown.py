"""Writeback adapter for local markdown files.

Inserts `![alt](relative/path.png)` after the paragraph matching the
mapping entry's `position` field. If position lookup fails, appends the
images at the end of the document with a marker comment so the user can
manually relocate them.

Backup: writes the original file to `<file>.bak` before modifying.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


def can_handle(source_type: str) -> bool:
    return source_type == "markdown"


def write(article_path: str, mapping: dict[str, Any]) -> dict[str, Any]:
    path = Path(article_path).resolve()
    if not path.is_file():
        return {"ok": False, "error": f"article file not found: {path}"}

    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup)

    text = path.read_text(encoding="utf-8")
    inserted: list[str] = []
    appended: list[str] = []

    for entry in mapping.get("mappings", []):
        if entry.get("status") != "ok":
            continue
        local_path = entry.get("local_path")
        if not local_path:
            continue
        alt = entry.get("alt_text") or entry.get("filename", "")
        position = entry.get("position", "")
        image_md = f"\n\n![{alt}]({local_path})\n"

        new_text, found = _insert_after_position(text, position, image_md)
        if found:
            text = new_text
            inserted.append(entry["filename"])
        else:
            appended.append(f"![{alt}]({local_path})")

    if appended:
        text += "\n\n<!-- composer: could not locate insertion points for the images below; please relocate manually -->\n\n"
        for line in appended:
            text += line + "\n\n"

    path.write_text(text, encoding="utf-8")
    return {
        "ok": True,
        "inserted": inserted,
        "appended": [a.split("](")[0][2:] for a in appended],
        "backup": str(backup),
    }


def _insert_after_position(text: str, position: str, image_md: str) -> tuple[str, bool]:
    """Find the paragraph matching `position` and insert image_md after it.

    `position` format from outline: "<section heading> / <paragraph snippet>"
    Strategy:
      1. If position has the "Section / Snippet" form, find the section
         heading first, then the snippet within that section.
      2. Otherwise, search for `position` as a literal substring and insert
         after the paragraph containing it.
    """
    if not position.strip():
        return text, False

    section_name = None
    snippet = position.strip()
    if " / " in position:
        section_name, snippet = position.split(" / ", 1)
        section_name = section_name.strip()
        snippet = snippet.strip()

    # Strip wrapping quotes from snippet
    if snippet.startswith('"') and snippet.endswith('"'):
        snippet = snippet[1:-1]

    lines = text.splitlines(keepends=False)
    section_start = 0
    section_end = len(lines)

    if section_name:
        for i, ln in enumerate(lines):
            if ln.strip().startswith("#"):
                heading = ln.lstrip("#").strip()
                if heading == section_name:
                    section_start = i + 1
                    # Find the end of this section (next same-or-higher heading)
                    h_level = len(ln) - len(ln.lstrip("#"))
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip().startswith("#"):
                            j_level = len(lines[j]) - len(lines[j].lstrip("#"))
                            if j_level <= h_level:
                                section_end = j
                                break
                    break
        else:
            # Section not found
            return text, False

    # Find snippet within the section window
    search_text = "\n".join(lines[section_start:section_end])
    snippet_lower = snippet.lower()[:60]  # first 60 chars, lowercased

    # Walk paragraphs and find one containing the snippet
    paragraphs = _walk_paragraphs(lines[section_start:section_end])
    for para_start, para_end, para_text in paragraphs:
        if snippet_lower in para_text.lower():
            insert_after = section_start + para_end
            new_lines = lines[:insert_after] + [image_md.rstrip("\n"), ""] + lines[insert_after:]
            return "\n".join(new_lines), True

    # Snippet not found in section; insert at the end of the section
    if section_name:
        new_lines = lines[:section_end] + [image_md.rstrip("\n"), ""] + lines[section_end:]
        return "\n".join(new_lines), True

    return text, False


def _walk_paragraphs(lines: list[str]) -> list[tuple[int, int, str]]:
    """Walk paragraphs in a line range, return (start_idx, end_idx_exclusive, text)."""
    paragraphs: list[tuple[int, int, str]] = []
    start = None
    buf: list[str] = []
    for i, ln in enumerate(lines):
        if ln.strip() and not ln.strip().startswith("#"):
            if start is None:
                start = i
            buf.append(ln)
        else:
            if start is not None and buf:
                paragraphs.append((start, i, "\n".join(buf)))
            start = None
            buf = []
    if start is not None and buf:
        paragraphs.append((start, len(lines), "\n".join(buf)))
    return paragraphs
