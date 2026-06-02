"""EXTEND.md preferences loader.

Search order:
  1. ./.illustration-composer/EXTEND.md (project-local)
  2. $XDG_CONFIG_HOME/illustration-composer/EXTEND.md (or $HOME/.config/...)
  3. $HOME/.illustration-composer/EXTEND.md

If no file is found, returns a sensible default dict — callers can run
first-time setup when the user actually needs to commit to choices.

The file is YAML (the schema described in references/preferences-schema.md).
Uses PyYAML if available; falls back to the tiny YAML parser if not.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


DEFAULT_PREFERENCES: dict[str, Any] = {
    "default_output_dir": "imgs-subdir",
    "default_backend": "openai_images",
    "default_model": None,
    "default_style": "editorial",
    "default_type": "infographic",
    "preferred_palette": None,
    "language": "en",
    "lock_language": False,
    "density": "per-section",
    "mode": "illustration",
    "watermark": {"enabled": False, "content": "", "position": "bottom-right"},
}


def search_paths() -> list[Path]:
    return [
        Path.cwd() / ".illustration-composer" / "EXTEND.md",
        Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
            / "illustration-composer" / "EXTEND.md",
        Path.home() / ".illustration-composer" / "EXTEND.md",
    ]


def load() -> tuple[dict[str, Any], Path | None]:
    """Return (preferences, source_path). source_path is None if defaults are used."""
    for path in search_paths():
        if path.is_file():
            data = _load_yaml(path)
            merged = _deep_merge(DEFAULT_PREFERENCES, data)
            return merged, path
    return dict(DEFAULT_PREFERENCES), None


def write_user_default(prefs: dict[str, Any]) -> Path:
    """Write to ~/.illustration-composer/EXTEND.md."""
    target = Path.home() / ".illustration-composer" / "EXTEND.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_dump_yaml(prefs), encoding="utf-8")
    return target


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml
        return yaml.safe_load(text) or {}
    except ImportError:
        return _tiny_yaml(text)


def _tiny_yaml(text: str) -> dict[str, Any]:
    """Minimal YAML parser sufficient for our preferences schema."""
    lines = text.splitlines()
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    for raw_line in lines:
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        content = line.strip()

        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]

        if ":" not in content:
            continue
        key, _, value = content.partition(":")
        key = key.strip().strip('"').strip("'")
        value = value.strip()

        if not value:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(value)
    return root


def _parse_scalar(value: str) -> Any:
    import re
    v = value.strip()
    if not v or v.lower() in ("null", "~"):
        return None
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    if v.startswith("{") and v.endswith("}"):
        inner = v[1:-1].strip()
        if not inner:
            return {}
        out = {}
        for pair in _split_top_level(inner, ","):
            k, _, val = pair.partition(":")
            out[k.strip().strip('"').strip("'")] = _parse_scalar(val.strip())
        return out
    return v


def _split_top_level(text: str, delim: str) -> list[str]:
    depth = 0
    parts: list[str] = []
    cur: list[str] = []
    for ch in text:
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
        if ch == delim and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur))
    return parts


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _dump_yaml(data: dict[str, Any], indent: int = 0) -> str:
    """Minimal YAML dumper — sufficient for preferences output."""
    lines: list[str] = []
    pad = " " * indent
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f"{pad}{k}:")
            lines.append(_dump_yaml(v, indent + 2).rstrip())
        elif isinstance(v, list):
            inner = ", ".join(_dump_scalar(x) for x in v)
            lines.append(f"{pad}{k}: [{inner}]")
        else:
            lines.append(f"{pad}{k}: {_dump_scalar(v)}")
    return "\n".join(lines) + "\n"


def _dump_scalar(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return str(v)
