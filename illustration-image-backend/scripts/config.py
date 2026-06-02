"""YAML config loader for illustration-image-backend.

Search order for the backends config:
  1. --config CLI arg
  2. $ILLUSTRATION_IMAGE_BACKEND_CONFIG env var
  3. ./illustration-image-backend.yaml (project-local)
  4. $XDG_CONFIG_HOME/illustration-image-backend/backends.yaml (or ~/.config/...)
  5. ~/.illustration-illustration-image-backend/backends.yaml

Returns an empty config dict if none found; callers fall back to defaults.

Uses PyYAML if installed; falls back to a tiny YAML subset parser if not,
sufficient for the example config schema (no anchors, no complex nesting).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _load_yaml_text(text: str) -> dict[str, Any]:
    try:
        import yaml
        return yaml.safe_load(text) or {}
    except ImportError:
        return _tiny_yaml(text)


def _tiny_yaml(text: str) -> dict[str, Any]:
    """Minimal YAML parser for our config schema.

    Handles: nested key: value mappings, scalar values (str/int/bool/null),
    inline flow mappings `{a: b, c: d}`, flow sequences `[a, b]`, comments.
    Does not handle: anchors, multi-line scalars, complex strings with colons.
    """
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
    if not v:
        return None
    if v.lower() in ("null", "~"):
        return None
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    if v.startswith("{") and v.endswith("}"):
        inner = v[1:-1].strip()
        if not inner:
            return {}
        out = {}
        for pair in _split_top_level(inner, ","):
            k, _, val = pair.partition(":")
            out[k.strip().strip('"').strip("'")] = _parse_scalar(val.strip())
        return out
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(p.strip()) for p in _split_top_level(inner, ",")]
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
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


def load_config(cli_path: str | None = None) -> dict[str, Any]:
    paths_to_try: list[Path] = []
    if cli_path:
        paths_to_try.append(Path(cli_path).expanduser())
    if env := os.environ.get("ILLUSTRATION_IMAGE_BACKEND_CONFIG"):
        paths_to_try.append(Path(env).expanduser())
    paths_to_try.extend([
        Path("illustration-image-backend.yaml"),
        Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
            / "illustration-image-backend" / "backends.yaml",
        Path.home() / ".illustration-image-backend" / "backends.yaml",
    ])
    for p in paths_to_try:
        if p.is_file():
            return _load_yaml_text(p.read_text(encoding="utf-8"))
    return {}


def resolve_backend_name(config: dict[str, Any], cli_backend: str | None) -> str:
    if cli_backend:
        return cli_backend
    return config.get("default_backend", "openai_images")


def resolve_alias(config: dict[str, Any], alias: str) -> tuple[str | None, str | None]:
    aliases = config.get("aliases", {}) or {}
    entry = aliases.get(alias)
    if not entry:
        return None, None
    return entry.get("backend"), entry.get("model")
