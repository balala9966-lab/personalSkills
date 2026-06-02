"""Ingest adapter for plain text / pasted content.

Used when:
  - source is a .txt file
  - source is "-" (stdin)
  - nothing else matched
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any


def detect(source: str) -> bool:
    if source == "-":
        return True
    if source.lower().endswith(".txt"):
        return Path(source).expanduser().is_file()
    return False


def load(source: str) -> dict[str, Any]:
    if source == "-":
        text = sys.stdin.read()
        title = _first_nonempty_line(text)[:80] or "pasted-content"
        source_dict = {"type": "text", "path": None, "title": title}
    else:
        path = Path(source).expanduser().resolve()
        text = path.read_text(encoding="utf-8")
        title = path.stem
        source_dict = {"type": "text", "path": str(path), "title": title}

    return {
        "title": title,
        "sections": [{
            "heading": "",
            "level": 0,
            "paragraphs": [p for p in text.split("\n\n") if p.strip()],
        }],
        "language": _detect_language(text),
        "word_count": _estimate_word_count(text),
        "source": source_dict,
        "raw": text,
    }


def _first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _detect_language(text: str) -> str:
    cjk = sum(1 for c in text if "一" <= c <= "鿿")
    if not text:
        return "en"
    return "zh" if cjk / len(text) > 0.3 else "en"


def _estimate_word_count(text: str) -> int:
    cjk = sum(1 for c in text if "一" <= c <= "鿿")
    ascii_words = len(re.findall(r"[A-Za-z]+", text))
    return ascii_words + cjk // 2
