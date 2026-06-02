"""Ingest adapter for local markdown files.

Returns a normalized Document with:
    - title: from the first H1, or filename if no H1
    - sections: list of {heading, level, paragraphs}
    - language: detected from content
    - word_count: rough estimate
    - source: dict with type/path
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def detect(source: str) -> bool:
    if source.lower().endswith((".md", ".markdown")):
        return Path(source).expanduser().is_file()
    return False


def load(source: str) -> dict[str, Any]:
    path = Path(source).expanduser().resolve()
    text = path.read_text(encoding="utf-8")
    title = _extract_title(text) or path.stem
    sections = _split_into_sections(text)
    return {
        "title": title,
        "sections": sections,
        "language": _detect_language(text),
        "word_count": _estimate_word_count(text),
        "source": {
            "type": "markdown",
            "path": str(path),
            "title": title,
        },
        "raw": text,
    }


def _extract_title(text: str) -> str | None:
    for line in text.splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m:
            return m.group(1).strip()
    return None


def _split_into_sections(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    para_lines: list[str] = []

    for line in text.splitlines():
        heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading_match:
            _flush_para(current, para_lines)
            para_lines = []
            current = {
                "heading": heading_match.group(2).strip(),
                "level": len(heading_match.group(1)),
                "paragraphs": [],
            }
            sections.append(current)
            continue
        if line.strip():
            para_lines.append(line)
        else:
            _flush_para(current, para_lines)
            para_lines = []

    _flush_para(current, para_lines)
    if not sections:
        # No headings at all — treat the whole doc as one section
        sections.append({
            "heading": "",
            "level": 0,
            "paragraphs": [p for p in text.split("\n\n") if p.strip()],
        })
    return sections


def _flush_para(section: dict[str, Any] | None, lines: list[str]) -> None:
    if section is None:
        return
    if not lines:
        return
    section["paragraphs"].append("\n".join(lines).strip())


def _detect_language(text: str) -> str:
    """Crude detection: if more than 30% of characters are CJK, return 'zh'."""
    cjk = sum(1 for c in text if "一" <= c <= "鿿")
    if not text:
        return "en"
    return "zh" if cjk / len(text) > 0.3 else "en"


def _estimate_word_count(text: str) -> int:
    """Approximate. For CJK, divide character count by 2 (rough Chinese-word equivalent)."""
    cjk = sum(1 for c in text if "一" <= c <= "鿿")
    ascii_words = len(re.findall(r"[A-Za-z]+", text))
    return ascii_words + cjk // 2
