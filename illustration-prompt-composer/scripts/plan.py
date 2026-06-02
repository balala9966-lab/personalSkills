#!/usr/bin/env python3
"""Step 3+4: turn analyzed source into a fully-populated outline.md + initial .mapping.json.

Reads the skeleton outline.md (from analyze.py) and replaces it with a
fully populated version including per-illustration blocks. Also writes an
initial .mapping.json with one pending entry per illustration.

Usage:
  python plan.py <source-or-workdir> [--preset X | --type Y --style Z]
                                     [--palette P] [--density D] [--mode M]
                                     [--aspect 16:9] [--image-count N]

The first positional arg can be:
  - the original source (path/URL) — script will locate the workdir from preferences
  - the workdir directly (containing outline.md)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any


def _setup_imports() -> None:
    here = Path(__file__).resolve().parent
    repo = here.parent
    for p in (here, repo / "adapters", repo / "adapters" / "ingest"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


_setup_imports()

import preferences           # noqa: E402
import styles_loader         # noqa: E402
import util                  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Step 3+4: plan illustrations and write outline + initial mapping.")
    p.add_argument("workdir_or_outline", help="Path to the workdir containing outline.md (from analyze.py).")
    p.add_argument("--preset", help="Style preset id. Overrides --type/--style.")
    p.add_argument("--type", dest="type_id")
    p.add_argument("--style", dest="style_id")
    p.add_argument("--palette")
    p.add_argument("--density", choices=["minimal", "balanced", "per-section", "rich"])
    p.add_argument("--mode", choices=["illustration", "cover", "both"], default="illustration")
    p.add_argument("--aspect", default="16:9")
    p.add_argument("--image-count", type=int, help="Override the auto-derived count.")
    p.add_argument("--language", help="Override label language (default: from skeleton).")
    args = p.parse_args()

    workdir = Path(args.workdir_or_outline).expanduser().resolve()
    if workdir.is_file() and workdir.name == "outline.md":
        workdir = workdir.parent
    outline_path = workdir / "outline.md"
    if not outline_path.is_file():
        print(f"error: outline.md not found in {workdir} (run analyze.py first)", file=sys.stderr)
        return 1

    skeleton = outline_path.read_text(encoding="utf-8")
    frontmatter, anchors = _parse_skeleton(skeleton)

    # Resolve type/style/palette from args, falling back to skeleton frontmatter
    if args.preset:
        preset = styles_loader.resolve_preset(args.preset)
        type_id = args.type_id or preset["type"]
        style_id = args.style_id or preset["style"]
        palette_id = args.palette or preset.get("palette") or frontmatter.get("palette") or ""
    else:
        type_id = args.type_id or frontmatter.get("type", "infographic")
        style_id = args.style_id or frontmatter.get("style", "editorial")
        palette_id = args.palette or frontmatter.get("palette", "")

    density = args.density or frontmatter.get("density", "balanced")
    language = args.language or frontmatter.get("language", "en")
    article_slug = frontmatter.get("article_slug", workdir.name)

    if args.mode == "cover":
        blocks = [_cover_block(style_id, palette_id, args.aspect, frontmatter.get("title", article_slug), language)]
    elif args.mode == "both":
        body_blocks = _body_blocks(anchors, type_id, args.image_count or len(anchors))
        blocks = [_cover_block(style_id, palette_id, args.aspect, frontmatter.get("title", article_slug), language)] + body_blocks
    else:
        target_count = args.image_count or len(anchors)
        blocks = _body_blocks(anchors, type_id, target_count)

    if not blocks:
        print("error: no illustration anchors found; refine density or check the analyze output", file=sys.stderr)
        return 1

    new_frontmatter = {
        **frontmatter,
        "type": type_id,
        "style": style_id,
        "palette": palette_id,
        "density": density,
        "image_count": len(blocks),
        "mode": args.mode,
        "aspect": args.aspect,
        "language": language,
    }
    new_outline = _render_outline(new_frontmatter, blocks)
    outline_path.write_text(new_outline, encoding="utf-8")
    print(f"[plan] wrote {outline_path} ({len(blocks)} illustrations)", file=sys.stderr)

    # Initial .mapping.json with pending entries
    mapping = {
        "article_slug": article_slug,
        "source": _source_from_frontmatter(frontmatter, workdir),
        "output_dir": str(workdir),
        "mode": args.mode,
        "default_output_dir_kind": frontmatter.get("output_dir_kind") or "imgs-subdir",
        "mappings": [
            {
                "illustration_id": _block_id(b, i),
                "filename": _filename_from_block(b),
                "status": "pending",
                "prompt_file": f"prompts/{_filename_from_block(b).replace('.png', '.md')}",
                "position": _field_from_block(b, "Position") or "",
                "updated_at": _now_iso(),
            }
            for i, b in enumerate(blocks, start=1)
        ],
    }
    util.write_mapping(workdir, mapping)
    print(f"[plan] wrote {workdir / '.mapping.json'}", file=sys.stderr)
    return 0


def _parse_skeleton(text: str) -> tuple[dict, list[dict]]:
    # Frontmatter
    fm: dict = {}
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end > 0:
            fm = _parse_yaml_block(text[4:end])
            body = text[end + 5:]

    # Candidate anchors from the skeleton comment
    anchors: list[dict] = []
    in_comment = False
    in_anchors = False
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("<!--"):
            in_comment = True
            continue
        if s.startswith("-->"):
            in_comment = False
            continue
        if in_comment and s.startswith("Candidate"):
            in_anchors = True
            continue
        if in_comment and in_anchors and s.startswith("- "):
            anchors.append({"position": s[2:].strip()})
        elif in_comment and in_anchors and not s.startswith("-"):
            in_anchors = False
    return fm, anchors


def _parse_yaml_block(text: str) -> dict:
    out: dict = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].rstrip()
        if not line.strip() or ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip()
        v = v.strip()
        if not v:
            continue
        out[k] = v
    return out


def _body_blocks(anchors: list[dict], type_id: str, target_count: int) -> list[dict]:
    """Produce one block per anchor, up to target_count."""
    blocks: list[dict] = []
    for i, anchor in enumerate(anchors[:target_count], start=1):
        position = anchor["position"]
        slug = _slugify_position(position)
        blocks.append({
            "kind": "body",
            "index": i,
            "filename": f"{i:02d}-{type_id}-{slug}.png",
            "fields": {
                "Position": position,
                "Purpose": "<one-sentence justification — replace with why an image here helps the reader>",
                "Visual Content": "- <visual element 1>\n- <visual element 2>\n- <visual element 3>",
                "Type Application": f"{type_id} — <how this type expresses the concept>",
                "Filename": f"{i:02d}-{type_id}-{slug}.png",
            },
        })
    return blocks


def _cover_block(style_id: str, palette_id: str, aspect: str, title: str, language: str) -> dict:
    return {
        "kind": "cover",
        "index": 0,
        "filename": "cover.png",
        "fields": {
            "Type": "hero",
            "Style": style_id,
            "Palette": palette_id,
            "Title": title,
            "Subtitle": "",
            "Text Level": "title-only",
            "Mood": "balanced",
            "Aspect": aspect,
            "Visual Content": "- <element 1>\n- <element 2>",
            "Filename": "cover.png",
        },
    }


def _slugify_position(position: str) -> str:
    # Position is "<section> / <snippet>"; use just the section for the slug
    section = position.split(" / ", 1)[0].strip()
    slug = re.sub(r"[/\\:*?\"<>|]+", "-", section)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^\w\-一-鿿]+", "", slug, flags=re.UNICODE)
    slug = slug.strip("-").lower()
    return slug[:30] or "anchor"


def _block_id(block: dict, idx: int) -> str:
    if block["kind"] == "cover":
        return "cover"
    return f"{idx:02d}"


def _filename_from_block(block: dict) -> str:
    return block["fields"]["Filename"]


def _field_from_block(block: dict, name: str) -> str:
    return block["fields"].get(name, "")


def _render_outline(fm: dict, blocks: list[dict]) -> str:
    lines = ["---"]
    for k in [
        "article_slug", "title", "type", "style", "palette", "density",
        "image_count", "mode", "language", "aspect",
        "content_type", "recommended_preset", "alternate_preset",
        "source_type", "source_path", "source_url", "doc_id", "output_dir_kind",
    ]:
        if k in fm and fm[k] not in ("", None):
            lines.append(f"{k}: {fm[k]}")
    lines.append("---")
    lines.append("")

    for block in blocks:
        if block["kind"] == "cover":
            lines.append("## Cover")
            lines.append("")
        else:
            lines.append(f"## Illustration {block['index']}")
            lines.append("")
        for fname in ["Type", "Style", "Palette", "Title", "Subtitle", "Text Level",
                      "Mood", "Aspect", "Position", "Purpose", "Visual Content",
                      "Type Application", "References", "Reference Usage", "Filename"]:
            if fname in block["fields"]:
                val = block["fields"][fname]
                if "\n" in val:
                    lines.append(f"**{fname}**:")
                    lines.append(val)
                else:
                    lines.append(f"**{fname}**: {val}")
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _source_from_frontmatter(fm: dict, workdir: Path) -> dict:
    return {
        "type": fm.get("source_type", "markdown"),
        "path": fm.get("source_path"),
        "url": fm.get("source_url"),
        "doc_id": fm.get("doc_id"),
        "title": fm.get("title"),
    }


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


if __name__ == "__main__":
    sys.exit(main())
