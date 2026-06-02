---
name: illustration-styles
description: Knowledge base of illustration styles, types, palettes, and presets for AI image generation. Use this skill when you need to look up which visual style fits a piece of content, compare Type × Style compatibility, pick a palette, or resolve a preset shortcut into its component type+style. Triggered passively by other illustration / cover / shot-list skills that need style metadata. Trigger words: 插图风格, 配图风格, illustration style, style preset, palette, type style compatibility.
---

# Illustration Styles Knowledge Base

A pure-knowledge skill: 6 Types × 23 Styles × 11 Palettes × 19 Presets, with a Type × Style compatibility matrix and content-type → preset auto-recommend rules.

This skill contains **no executable code**. It exists so prompt-composing skills (and humans) can look up style metadata in one place instead of duplicating it across many skills.

## What This Provides

- **Types** (`references/types.md`) — 6 ways an illustration can structure information: `infographic`, `scene`, `flowchart`, `comparison`, `framework`, `timeline`.
- **Styles** (`references/styles.md` + `styles/*.md`) — 23 visual styles, grouped into families (flat, hand-drawn, technical, artistic, poster, special).
- **Palettes** (`references/palettes.md` + `palettes/*.md`) — 11 color palettes for both body illustrations and covers.
- **Presets** (`references/presets.md` + `presets/*.md`) — 19 named Type+Style combos for common content categories.
- **Compatibility matrix** (`references/compatibility.md`) — which Style works with which Type, with `strong / ok / avoid` ratings.
- **Auto-recommend rules** (`references/auto-recommend.md`) — given a content type (technical / tutorial / narrative / opinion / ...), which preset to suggest first.
- **Machine-readable index** (`references/index.json`) — the same data in JSON, for programmatic consumption by composer skills.

## How To Use

**Human reading**: open `references/` and browse. The `.md` files are the source of truth and are written for humans.

**Composer skills**: read `references/index.json` first. Each style/palette/preset entry has a `doc` field pointing to the human-readable detail page; load that on demand.

```python
import json, pathlib
styles_home = pathlib.Path(os.environ.get("ILLUSTRATION_STYLES_HOME",
    "~/.claude/skills/illustration-styles")).expanduser()
index = json.loads((styles_home / "references/index.json").read_text())

# Resolve a preset
preset = next(p for p in index["presets"] if p["id"] == "tech-explainer")
# → {"type": "infographic", "style": "blueprint", "use_case": "..."}

# Check compatibility
style = next(s for s in index["styles"] if s["id"] == "blueprint")
rating = style["compat_types"]["scene"]  # → "avoid"
```

## How To Extend

To add a new style:

1. Pick a stable kebab-case `id` (e.g. `risograph`).
2. Add a detail page at `styles/<id>.md` following the template in `styles/_template.md`.
3. Add an entry to `references/index.json` under `styles[]` with `id`, `family`, `compat_types`, and `doc`.
4. Update `references/styles.md` (the human index) and `references/compatibility.md` (the matrix).

Same shape for palettes (`palettes/`) and presets (`presets/`).

The compatibility ratings are subjective — `strong` means the combo is recommended and produces consistent results across generations; `ok` means it works but is not the obvious first pick; `avoid` means the combo tends to fight itself visually (e.g. `blueprint` + `scene`).

## Not In Scope

- This skill does not call image-generation APIs. That belongs to `illustration-image-backend`.
- This skill does not compose prompts. That belongs to `illustration-prompt-composer`.
- This skill does not opinionate on which generator (OpenAI / Gemini / etc.) renders a given style best — that's a backend capability question, not a style question.
