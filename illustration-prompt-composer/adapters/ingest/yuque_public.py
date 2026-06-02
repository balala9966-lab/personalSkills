"""Ingest adapter for public yuque URLs (yuque.com/...).

Public yuque docs can be fetched via the public API at yuque.com/api/v2/...
but the canonical user-facing path is to use the WebFetch tool from the
Claude harness. This adapter declares the source type and returns a stub
document with the URL; the actual fetch is delegated to the calling
script, which uses Claude's WebFetch tool to download and pass back the
HTML/markdown body.

When invoked from a CLI without Claude in the loop, the adapter falls
back to urllib + a simple HTML-to-text extraction so the script still
runs (with reduced quality).
"""

from __future__ import annotations

import html as html_mod
import re
from typing import Any
from urllib.parse import urlparse


def detect(source: str) -> bool:
    if not source.startswith(("http://", "https://")):
        return False
    host = urlparse(source).netloc.lower()
    return host.endswith("yuque.com")


def load(source: str, prefetched_body: str | None = None) -> dict[str, Any]:
    """Load a public yuque doc.

    If `prefetched_body` is provided, use it as the article body (preferred:
    pass markdown fetched by Claude's WebFetch tool). Otherwise fall back to
    a basic urllib fetch + HTML-to-text strip.
    """
    body = prefetched_body or _fetch_via_urllib(source)
    sections = _split_into_sections(body)
    title = _extract_title(body) or _slug_from_url(source)
    return {
        "title": title,
        "sections": sections,
        "language": _detect_language(body),
        "word_count": _estimate_word_count(body),
        "source": {
            "type": "yuque_public",
            "url": source,
            "title": title,
        },
        "raw": body,
    }


def _fetch_via_urllib(url: str) -> str:
    import urllib.request, urllib.error
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "illustration-composer/0.1"})
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", errors="replace")
        return _html_to_text(html)
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"could not fetch {url}: {e}. "
            f"prefer calling Claude's WebFetch tool and passing the result as prefetched_body."
        )


def _html_to_text(html: str) -> str:
    """Very rough HTML→text. Loses markdown structure."""
    text = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<h([1-6])[^>]*>(.*?)</h\1>", lambda m: f"\n{'#' * int(m.group(1))} {m.group(2)}\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_mod.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _extract_title(text: str) -> str | None:
    for line in text.splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m:
            return m.group(1).strip()
    return None


def _slug_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1] or "yuque-public-doc"


def _split_into_sections(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    para_lines: list[str] = []

    for line in text.splitlines():
        heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading_match:
            if current and para_lines:
                current["paragraphs"].append("\n".join(para_lines).strip())
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
        elif current and para_lines:
            current["paragraphs"].append("\n".join(para_lines).strip())
            para_lines = []

    if current and para_lines:
        current["paragraphs"].append("\n".join(para_lines).strip())
    if not sections:
        sections.append({"heading": "", "level": 0,
                         "paragraphs": [p for p in text.split("\n\n") if p.strip()]})
    return sections


def _detect_language(text: str) -> str:
    cjk = sum(1 for c in text if "一" <= c <= "鿿")
    if not text:
        return "en"
    return "zh" if cjk / len(text) > 0.3 else "en"


def _estimate_word_count(text: str) -> int:
    cjk = sum(1 for c in text if "一" <= c <= "鿿")
    ascii_words = len(re.findall(r"[A-Za-z]+", text))
    return ascii_words + cjk // 2
