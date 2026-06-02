"""Shared utilities for composer scripts.

- Path resolution for sibling skills (illustration-styles, illustration-image-backend).
- Slug generation.
- Mapping.json atomic writes.
- Output directory layout helpers.

These functions are intentionally pure — no global state, no implicit IO
beyond what's necessary.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Sibling skill resolution
# ---------------------------------------------------------------------------

def resolve_sibling_skill(env_var: str, dir_name: str) -> Path:
    """Find an installed sibling skill (illustration-image-backend or illustration-styles).

    Search order:
      1. Env var ($ILLUSTRATION_IMAGE_BACKEND_HOME, $ILLUSTRATION_STYLES_HOME, etc.)
      2. Sibling in the same parent directory as this composer (monorepo case)
      3. ~/.claude/skills/<dir_name>
      4. ~/.codefuse/fuse/skills/<dir_name>

    Raises FileNotFoundError with an actionable message if not found.
    """
    if env := os.environ.get(env_var):
        path = Path(env).expanduser()
        if path.exists():
            return path

    composer_root = Path(__file__).resolve().parents[1]
    sibling = composer_root.parent / dir_name
    if sibling.exists():
        return sibling

    for candidate in [
        Path.home() / ".claude" / "skills" / dir_name,
        Path.home() / ".codefuse" / "fuse" / "skills" / dir_name,
    ]:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"sibling skill {dir_name!r} not found. set {env_var} or install it at one of:\n"
        f"  - {composer_root.parent / dir_name}\n"
        f"  - ~/.claude/skills/{dir_name}\n"
        f"  - ~/.codefuse/fuse/skills/{dir_name}"
    )


def styles_home() -> Path:
    return resolve_sibling_skill("ILLUSTRATION_STYLES_HOME", "illustration-styles")


def backend_home() -> Path:
    return resolve_sibling_skill("ILLUSTRATION_IMAGE_BACKEND_HOME", "illustration-image-backend")


# ---------------------------------------------------------------------------
# Slug generation
# ---------------------------------------------------------------------------

def slugify(text: str, max_len: int = 60) -> str:
    """Generate a filesystem-safe slug. Preserves CJK characters."""
    text = text.strip()
    if not text:
        return "untitled"
    # Normalize unicode, strip control chars
    text = unicodedata.normalize("NFC", text)
    # Replace whitespace and common separators with hyphens
    text = re.sub(r"[\s/\\:*?\"<>|]+", "-", text)
    # Strip leading/trailing dashes
    text = text.strip("-")
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text or "untitled"


def article_slug_from_source(source: dict[str, Any]) -> str:
    """Derive an article slug from a source dict.

    source = {"type": "markdown"|"yuque_internal"|"yuque_public"|"text",
              "path": str|None, "url": str|None, "doc_id": str|None,
              "title": str|None}
    """
    if title := source.get("title"):
        return slugify(title)
    if path := source.get("path"):
        return slugify(Path(path).stem)
    if url := source.get("url"):
        last = url.rstrip("/").split("/")[-1]
        return slugify(last)
    if doc_id := source.get("doc_id"):
        return f"doc-{doc_id}"
    return "untitled"


# ---------------------------------------------------------------------------
# Output layout
# ---------------------------------------------------------------------------

def compute_output_root(
    source: dict[str, Any],
    output_dir_kind: str,
    cwd: Path | None = None,
) -> Path:
    """Determine the {output_root} based on EXTEND.md's default_output_dir.

    For markdown sources, {output_root} is relative to the article's directory.
    For URL / paste sources, falls back to `independent` semantics.
    """
    cwd = cwd or Path.cwd()
    if source.get("type") == "markdown" and source.get("path"):
        article_dir = Path(source["path"]).resolve().parent
        if output_dir_kind == "imgs-subdir":
            return article_dir / "imgs"
        if output_dir_kind == "same-dir":
            return article_dir
        if output_dir_kind == "illustrations-subdir":
            return article_dir / "illustrations"
        if output_dir_kind == "independent":
            return cwd / "illustrations"
        raise ValueError(f"unknown default_output_dir: {output_dir_kind!r}")

    # Non-markdown sources always use independent layout
    return cwd / "illustrations"


def article_workdir(output_root: Path, article_slug: str) -> Path:
    return output_root / article_slug


def markdown_image_path(
    local_path_abs: Path,
    article_source_path: Path | None,
    output_dir_kind: str,
) -> str:
    """Compute the relative path to use in markdown image syntax.

    For markdown sources, this is relative to the article file's directory.
    For non-markdown sources, returns an absolute path.
    """
    if article_source_path is None:
        return str(local_path_abs)
    try:
        rel = local_path_abs.relative_to(article_source_path.parent)
        return str(rel).replace("\\", "/")
    except ValueError:
        return str(local_path_abs)


# ---------------------------------------------------------------------------
# .mapping.json atomic writes
# ---------------------------------------------------------------------------

def load_mapping(workdir: Path) -> dict[str, Any]:
    path = workdir / ".mapping.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_mapping(workdir: Path, data: dict[str, Any]) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    target = workdir / ".mapping.json"
    tmp = workdir / ".mapping.json.tmp"
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, target)
