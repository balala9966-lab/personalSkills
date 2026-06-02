#!/usr/bin/env python3
"""CLI entrypoint for illustration-image-backend.

Usage:

  python scripts/generate.py --prompt "..." --backend openai_images \
      --width 1536 --height 1024 --out-json /tmp/result.json

  python scripts/generate.py --request /tmp/request.json --backend openai_images

  python scripts/generate.py --alias banana --prompt "..."

Exit codes:
  0 success
  1 bad arguments / missing config
  2 backend reported an error (network, API, CLI failure)
  3 unexpected exception

Stdout: absolute path to each saved PNG, one per line.
Stderr: progress and errors.
--out-json: full GenerateResponse as JSON (preferred for programmatic use).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _setup_imports() -> None:
    here = Path(__file__).resolve().parent
    repo = here.parent
    for p in (here, repo / "adapters"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


_setup_imports()

import base as base_mod          # noqa: E402
import config as config_mod      # noqa: E402
import registry as registry_mod  # noqa: E402


def _load_all_adapters() -> None:
    """Import every adapter so each module's register() runs."""
    adapters_dir = Path(__file__).resolve().parent.parent / "adapters"
    for py in sorted(adapters_dir.glob("*.py")):
        if py.stem.startswith("_"):
            continue
        __import__(py.stem)


def main() -> int:
    _load_all_adapters()

    p = argparse.ArgumentParser(description="Generate an image via a pluggable backend.")
    p.add_argument("--prompt", help="Prompt text (if not using --request).")
    p.add_argument("--request", help="Path to a JSON file containing a GenerateRequest.")
    p.add_argument("--config", help="Path to backends.yaml. Default locations are searched if omitted.")
    p.add_argument("--backend", help="Backend name from backends.yaml. Defaults to config's default_backend.")
    p.add_argument("--alias", help="Resolve a backend+model alias from backends.yaml aliases.")
    p.add_argument("--model", help="Override the backend's default model.")
    p.add_argument("--width", type=int, default=1024)
    p.add_argument("--height", type=int, default=1024)
    p.add_argument("--n", type=int, default=1)
    p.add_argument("--output-dir", default=".image_process")
    p.add_argument("--filename", help="Output filename. Only honored when n=1.")
    p.add_argument("--seed", type=int)
    p.add_argument("--negative-prompt")
    p.add_argument("--ref", action="append", default=[],
                   help="Reference image. Format: PATH or PATH:ROLE where ROLE is direct|style|palette. Repeatable.")
    p.add_argument("--out-json", help="Write the full GenerateResponse JSON here.")
    p.add_argument("--list-backends", action="store_true")

    args = p.parse_args()

    if args.list_backends:
        for name in registry_mod.list_backends():
            print(name)
        return 0

    config = config_mod.load_config(args.config)

    backend_name = None
    alias_model = None
    if args.alias:
        backend_name, alias_model = config_mod.resolve_alias(config, args.alias)
        if not backend_name:
            print(f"error: alias {args.alias!r} not found in config", file=sys.stderr)
            return 1
    backend_name = args.backend or backend_name or config_mod.resolve_backend_name(config, None)

    backends_section = (config.get("backends") or {})
    backend_config = backends_section.get(backend_name) or {}
    if not backend_config:
        print(f"warning: backend {backend_name!r} not found in config; using defaults", file=sys.stderr)
        backend_config = {"type": backend_name}
    backend_type = backend_config.get("type", backend_name)

    try:
        backend = registry_mod.get_backend(backend_type, backend_config)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.request:
        req_data = json.loads(Path(args.request).read_text())
        req = base_mod.request_from_dict(req_data)
    else:
        if not args.prompt:
            print("error: --prompt or --request required", file=sys.stderr)
            return 1
        refs = []
        for r in args.ref:
            path, _, role = r.partition(":")
            refs.append(base_mod.Reference(path=path, role=role or "direct"))
        req = base_mod.GenerateRequest(
            prompt=args.prompt,
            negative_prompt=args.negative_prompt,
            width=args.width, height=args.height,
            n=args.n, seed=args.seed,
            refs=refs,
            output_dir=args.output_dir,
            filename=args.filename,
            model=args.model or alias_model,
        )

    print(f"[illustration-image-backend] backend={backend.name} model={req.model or 'default'} "
          f"size={req.width}x{req.height} n={req.n}", file=sys.stderr)

    try:
        resp = backend.generate(req)
    except Exception as e:
        print(f"error: unexpected: {e}", file=sys.stderr)
        return 3

    if args.out_json:
        Path(args.out_json).write_text(json.dumps(resp.to_dict(), indent=2, ensure_ascii=False))

    if not resp.ok:
        err = resp.error
        print(f"[illustration-image-backend] FAILED code={err.code} {err.message}", file=sys.stderr)
        return 2

    for img in resp.images:
        print(img.path)
        print(f"[illustration-image-backend] saved {img.path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
