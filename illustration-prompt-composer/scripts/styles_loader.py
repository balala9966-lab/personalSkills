"""Load the illustration-styles index and resolve styles/palettes/presets."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import util


@lru_cache(maxsize=1)
def index() -> dict[str, Any]:
    path = util.styles_home() / "references" / "index.json"
    if not path.is_file():
        raise FileNotFoundError(f"illustration-styles index not found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_preset(preset_id: str) -> dict[str, Any]:
    for p in index()["presets"]:
        if p["id"] == preset_id:
            return p
    raise ValueError(f"unknown preset {preset_id!r}. "
                     f"valid: {[p['id'] for p in index()['presets']]}")


def resolve_style(style_id: str) -> dict[str, Any]:
    for s in index()["styles"]:
        if s["id"] == style_id:
            return s
    raise ValueError(f"unknown style {style_id!r}")


def resolve_palette(palette_id: str) -> dict[str, Any]:
    for p in index()["palettes"]:
        if p["id"] == palette_id:
            return p
    raise ValueError(f"unknown palette {palette_id!r}")


def style_detail(style_id: str) -> str:
    """Load the full style detail markdown for prompt composition."""
    style = resolve_style(style_id)
    detail_path = util.styles_home() / style["doc"]
    if detail_path.is_file():
        return detail_path.read_text(encoding="utf-8")
    return ""


def palette_detail(palette_id: str) -> str:
    palette = resolve_palette(palette_id)
    detail_path = util.styles_home() / palette["doc"]
    if detail_path.is_file():
        return detail_path.read_text(encoding="utf-8")
    return ""


def auto_recommend_preset(content_type: str) -> tuple[str, str]:
    """Return (first_preset, alt_preset) for a given content_type.

    Falls back to (knowledge-base, tech-explainer) if content_type unknown.
    """
    table = index().get("auto_recommend", {})
    entry = table.get(content_type) or table.get("unknown")
    if not entry:
        return "knowledge-base", "tech-explainer"
    return entry.get("first", "knowledge-base"), entry.get("alt", "tech-explainer")


def density_for_word_count(words: int) -> str:
    """Recommend density based on article length."""
    for tier in index().get("density_by_word_count", []):
        max_w = tier.get("max_words")
        if max_w is None or words <= max_w:
            return tier.get("density", "balanced")
    return "per-section"


def compatibility(style_id: str, type_id: str) -> str:
    """Return 'strong' | 'ok' | 'avoid' for a Style x Type combo. Returns 'ok' if unknown."""
    try:
        style = resolve_style(style_id)
        return style.get("compat_types", {}).get(type_id, "ok")
    except ValueError:
        return "ok"


def extract_prompt_hints(detail_md: str) -> tuple[list[str], list[str]]:
    """Pull 'Include' and 'Avoid' phrases from a style/palette detail page.

    Looks for the 'Generation Prompt Hints' section and parses bullet/line content.
    Returns (include_phrases, avoid_phrases).
    """
    if not detail_md:
        return [], []
    lines = detail_md.splitlines()
    in_hints = False
    in_include = False
    in_avoid = False
    include: list[str] = []
    avoid: list[str] = []

    for ln in lines:
        s = ln.strip()
        if s.startswith("## ") and "Prompt Hints" in s:
            in_hints = True
            continue
        if in_hints and s.startswith("## "):
            break
        if not in_hints:
            continue
        sl = s.lower()
        if sl.startswith("include"):
            in_include, in_avoid = True, False
            content = s.split(":", 1)[1].strip() if ":" in s else ""
            if content:
                include.append(_strip_quotes(content))
            continue
        if sl.startswith("avoid"):
            in_include, in_avoid = False, True
            content = s.split(":", 1)[1].strip() if ":" in s else ""
            if content:
                avoid.append(_strip_quotes(content))
            continue
        if s.startswith("- "):
            text = _strip_quotes(s[2:].strip())
            if in_include:
                include.append(text)
            elif in_avoid:
                avoid.append(text)

    return include, avoid


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s
