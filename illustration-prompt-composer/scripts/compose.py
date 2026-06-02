#!/usr/bin/env python3
"""Step 5: turn outline.md blocks into prompts/NN-*.md files.

For each illustration block in outline.md, compose a full image-generation
prompt using the per-Type template from references/prompt-templates.md
plus the style and palette hint phrases pulled from illustration-styles.

The output prompt files are what `dispatch.py` feeds to illustration-image-backend.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path


def _setup_imports() -> None:
    here = Path(__file__).resolve().parent
    repo = here.parent
    for p in (here, repo / "adapters", repo / "adapters" / "ingest"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


_setup_imports()

import styles_loader  # noqa: E402
import util           # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Step 5: compose prompt files from outline.md.")
    p.add_argument("workdir", help="Path to the article workdir containing outline.md.")
    args = p.parse_args()

    workdir = Path(args.workdir).expanduser().resolve()
    if workdir.is_file() and workdir.name == ".mapping.json":
        workdir = workdir.parent
    outline_path = workdir / "outline.md"
    if not outline_path.is_file():
        print(f"error: outline.md not found in {workdir}", file=sys.stderr)
        return 1

    text = outline_path.read_text(encoding="utf-8")
    frontmatter, blocks = _parse_outline(text)

    style_id = frontmatter.get("style", "editorial")
    palette_id = frontmatter.get("palette") or ""
    aspect = frontmatter.get("aspect", "16:9")
    language = frontmatter.get("language", "en")

    style_detail = styles_loader.style_detail(style_id)
    style_include, style_avoid = styles_loader.extract_prompt_hints(style_detail)

    palette_detail = ""
    palette_include: list[str] = []
    if palette_id:
        try:
            palette_detail = styles_loader.palette_detail(palette_id)
            palette_include, _ = styles_loader.extract_prompt_hints(palette_detail)
        except ValueError:
            print(f"[compose] warning: palette {palette_id!r} not found; skipping palette hints",
                  file=sys.stderr)

    # Load extended IP description for ink-notes style
    ip_description = ""
    if style_id == "ink-notes":
        ip_description = _load_ink_notes_ip()

    prompts_dir = workdir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for block in blocks:
        prompt_text = _compose_prompt(
            block=block,
            type_id=block.get("type_override") or frontmatter.get("type", "infographic"),
            style_id=style_id,
            palette_id=palette_id,
            aspect=block.get("Aspect") or aspect,
            language=language,
            style_include=style_include,
            style_avoid=style_avoid,
            palette_include=palette_include,
            ip_description=ip_description,
        )
        prompt_path = _backup_then_write(prompts_dir, block, prompt_text)
        written.append(prompt_path.name)
        print(f"[compose] wrote {prompt_path}", file=sys.stderr)

    print(f"[compose] {len(written)} prompt files in {prompts_dir}", file=sys.stderr)
    for w in written:
        print(w)
    return 0


def _parse_outline(text: str) -> tuple[dict, list[dict]]:
    fm: dict = {}
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end > 0:
            for line in text[4:end].splitlines():
                line = line.split("#", 1)[0].rstrip()
                if ":" in line:
                    k, _, v = line.partition(":")
                    fm[k.strip()] = v.strip()
            body = text[end + 5:]

    blocks: list[dict] = []
    current: dict | None = None
    current_field: str | None = None
    current_field_lines: list[str] = []

    def flush_field():
        nonlocal current_field, current_field_lines
        if current and current_field:
            current[current_field] = "\n".join(current_field_lines).strip()
        current_field = None
        current_field_lines = []

    for line in body.splitlines():
        m_heading = re.match(r"^##\s+(.+?)\s*$", line)
        if m_heading:
            flush_field()
            if current:
                blocks.append(current)
            heading = m_heading.group(1).strip()
            current = {"_heading": heading, "_kind": "cover" if heading.lower() == "cover" else "body"}
            continue
        m_field = re.match(r"^\*\*(.+?)\*\*:\s*(.*)$", line)
        if m_field:
            flush_field()
            current_field = m_field.group(1).strip()
            tail = m_field.group(2).strip()
            current_field_lines = [tail] if tail else []
            continue
        if current_field is not None:
            if line.strip().startswith("- ") or line.startswith(" ") or line.strip():
                current_field_lines.append(line)
            else:
                flush_field()
    flush_field()
    if current:
        blocks.append(current)

    return fm, blocks


def _load_ink_notes_ip() -> str:
    """Load the default IP character description from ink-notes-extended."""
    ip_path = util.styles_home() / "styles" / "ink-notes-extended" / "default-ip.md"
    if not ip_path.is_file():
        return ""
    text = ip_path.read_text(encoding="utf-8")
    # Extract the active IP's visual traits section
    # Prefer 贵公子 if reference image exists, else The Tinkerer
    ref_img = util.styles_home() / "assets" / "character-references" / "贵公子.png"
    if ref_img.is_file():
        # Extract Option B section
        start = text.find("## Option B:")
        if start >= 0:
            end = text.find("\n## ", start + 10)
            section = text[start:end] if end > 0 else text[start:]
            # Pull just the visual traits for prompt embedding
            traits_start = section.find("### Visual Traits")
            if traits_start >= 0:
                traits_end = section.find("### ", traits_start + 10)
                traits = section[traits_start:traits_end].strip() if traits_end > 0 else section[traits_start:].strip()
                return (
                    "Character: 贵公子 (a cute ancient-Chinese-style young boy) is the active subject, "
                    "doing [CORE ACTION]. Traits from reference image: round oversized head with short neat dark hair, "
                    "big expressive eyes, light celadon/mint-green hanfu robe with white inner layer, "
                    "teal waist sash with a small jade pendant (the silhouette signature), "
                    "toddler-like proportions, small rounded hands actively doing the action, "
                    "cloth shoes matching the robe. When rendered in ink-notes style, keep celadon green "
                    "as the ONE accent color on the character; scene uses standard ink-notes palette. "
                    "The character must drive the core action — not stand aside, not narrate, not decorate. "
                    "Reference: assets/character-references/贵公子.png"
                )
    # Fallback to Tinkerer
    return (
        "Character: The Tinkerer is the active subject, doing [CORE ACTION]. "
        "Traits: round head with two small upright tufts (silhouette signature), "
        "two dot eyes, tiny neutral mouth, plain white coverall with no logo/text, "
        "mitten-like hands actively doing the action, plain rounded shoes. "
        "Body is black line work only — no colored fill. "
        "The character must drive the core action — not stand aside, not narrate, not decorate."
    )


def _compose_prompt(
    block: dict,
    type_id: str,
    style_id: str,
    palette_id: str,
    aspect: str,
    language: str,
    style_include: list[str],
    style_avoid: list[str],
    palette_include: list[str],
    ip_description: str = "",
) -> str:
    is_cover = block.get("_kind") == "cover"
    size_descriptor = "cover hero" if is_cover else "editorial body"
    style_phrases = "; ".join(style_include) or "thin black hand-drawn line work, clean composition"
    palette_phrases = "; ".join(palette_include) or "restrained color use"

    fm_lines = [
        "---",
        f"illustration_id: {block.get('_heading', '').lower().replace(' ', '-')}",
        f"type: {type_id}",
        f"style: {style_id}",
        f"palette: {palette_id}",
        f"aspect: {aspect}",
        "---",
        "",
    ]

    if is_cover:
        body = _compose_cover(block, aspect, size_descriptor, style_phrases, palette_phrases, style_avoid)
    else:
        body = _compose_body(block, type_id, aspect, size_descriptor, style_phrases, palette_phrases, language, style_avoid, ip_description)

    return "\n".join(fm_lines) + body + "\n\n" + _universal_avoid_tail()


def _compose_body(block, type_id, aspect, size_descriptor, style_phrases, palette_phrases, language, style_avoid, ip_description=""):
    purpose = block.get("Purpose", "").strip()
    visual = block.get("Visual Content", "").strip()
    type_app = block.get("Type Application", "").strip()
    references = block.get("References", "").strip()

    avoid_phrases = "; ".join(style_avoid) or "none specified"

    lines = [
        f"Create a {aspect} {size_descriptor} illustration.",
        "",
        f"Style: {style_phrases}",
        f"Palette: {palette_phrases}",
        "",
    ]
    if ip_description:
        lines.append(ip_description)
        lines.append("")
    lines.extend([
        f"Subject: {purpose}",
        "",
        "Visual content:",
        visual,
        "",
    ])
    if type_app:
        lines.append(f"Type application ({type_id}): {type_app}")
        lines.append("")
    lines.extend([
        f"Language for any text/labels: {language}.",
        "",
        f"Avoid: {avoid_phrases}.",
    ])
    if references:
        lines.append("")
        lines.append(f"Reference images: {references}.")
    return "\n".join(lines)


def _compose_cover(block, aspect, size_descriptor, style_phrases, palette_phrases, style_avoid):
    title = block.get("Title", "").strip()
    subtitle = block.get("Subtitle", "").strip()
    text_level = block.get("Text Level", "title-only").strip()
    mood = block.get("Mood", "balanced").strip()
    cover_type = block.get("Type", "hero").strip()
    visual = block.get("Visual Content", "").strip()
    avoid_phrases = "; ".join(style_avoid) or "none specified"

    lines = [
        f"Create a {aspect} cover image ({size_descriptor}).",
        "",
        f"Style: {style_phrases}",
        f"Palette: {palette_phrases}",
        "",
        f"Composition: {cover_type} composition.",
        "",
    ]
    if visual:
        lines.append("Visual content:")
        lines.append(visual)
        lines.append("")
    if text_level != "none" and title:
        lines.append(f'Title (visible in image): "{title}"')
        if text_level in ("title-subtitle", "text-rich") and subtitle:
            lines.append(f'Subtitle (visible in image): "{subtitle}"')
        lines.append("Do not invent any text not provided above.")
        lines.append("")
    lines.append(f"Mood: {mood}.")
    lines.append("")
    lines.append(f"Avoid: {avoid_phrases}.")
    return "\n".join(lines)


def _universal_avoid_tail() -> str:
    return (
        "Additional constraints (always apply):\n"
        "- No company logos\n"
        "- No brand wordmarks\n"
        "- No readable text on character clothing other than labels explicitly listed above\n"
        "- No photorealistic faces of identifiable real people\n"
    )


def _backup_then_write(prompts_dir: Path, block: dict, prompt_text: str) -> Path:
    filename = block.get("Filename", "").strip()
    if not filename:
        raise ValueError(f"block {block.get('_heading')!r} missing Filename field")
    prompt_filename = filename.rsplit(".", 1)[0] + ".md"
    prompt_path = prompts_dir / prompt_filename

    if prompt_path.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = prompt_path.with_name(prompt_path.stem + f"-backup-{stamp}.md")
        prompt_path.rename(backup)
        print(f"[compose] existing prompt backed up to {backup.name}", file=sys.stderr)

    prompt_path.write_text(prompt_text, encoding="utf-8")
    return prompt_path


if __name__ == "__main__":
    sys.exit(main())
