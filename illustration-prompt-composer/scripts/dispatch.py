#!/usr/bin/env python3
"""Step 6: dispatch each pending mapping entry to illustration-image-backend, update .mapping.json.

For each entry with status=pending:
  1. Read the prompt file body
  2. Build a GenerateRequest JSON
  3. Subprocess `illustration-image-backend/scripts/generate.py --request <tmp> --out-json <tmp>`
  4. Parse the GenerateResponse; on ok=True, update mapping with paths and metadata
  5. On error, record the error and continue (does not crash other images)

Re-running is safe: by default skips entries that already have status=ok.
Use --regenerate-all or --regenerate <id1,id2> to force.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
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

import util  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Step 6: dispatch prompts to illustration-image-backend.")
    p.add_argument("workdir", help="Path to the article workdir.")
    p.add_argument("--backend", help="Override backend (default: from EXTEND.md or illustration-image-backend's default).")
    p.add_argument("--model", help="Override model.")
    p.add_argument("--alias", help="Use a backend alias instead of --backend/--model.")
    p.add_argument("--regenerate", help="Comma-separated illustration_ids to regenerate.")
    p.add_argument("--regenerate-all", action="store_true")
    p.add_argument("--max-retries", type=int, default=1, help="Retries per failed image.")
    p.add_argument("--config", help="Path to illustration-image-backend backends.yaml.")
    args = p.parse_args()

    workdir = Path(args.workdir).expanduser().resolve()
    if workdir.is_file() and workdir.name == ".mapping.json":
        workdir = workdir.parent

    mapping = util.load_mapping(workdir)
    if not mapping or not mapping.get("mappings"):
        print(f"error: no .mapping.json in {workdir} or no entries", file=sys.stderr)
        return 1

    outline_path = workdir / "outline.md"
    outline_text = outline_path.read_text(encoding="utf-8") if outline_path.is_file() else ""
    outline_fm = _parse_outline_frontmatter(outline_text)

    backend_script = util.backend_home() / "scripts" / "generate.py"
    if not backend_script.is_file():
        print(f"error: illustration-image-backend script not found at {backend_script}", file=sys.stderr)
        return 1

    regen_ids = set()
    if args.regenerate:
        regen_ids = set(s.strip() for s in args.regenerate.split(",") if s.strip())

    aspect = outline_fm.get("aspect", "16:9")
    width, height = _aspect_to_size(aspect)

    success = 0
    failed = 0
    skipped = 0

    for entry in mapping["mappings"]:
        if entry.get("status") == "ok" and not args.regenerate_all and entry["illustration_id"] not in regen_ids:
            skipped += 1
            continue

        prompt_file = workdir / entry["prompt_file"]
        if not prompt_file.is_file():
            entry["status"] = "error"
            entry["error"] = {"code": "PROMPT_MISSING",
                              "message": f"prompt file not found: {prompt_file}",
                              "attempts": 0}
            entry["updated_at"] = _now_iso()
            failed += 1
            continue

        prompt_body = _strip_frontmatter(prompt_file.read_text(encoding="utf-8")).strip()

        request_payload = {
            "prompt": prompt_body,
            "width": width,
            "height": height,
            "n": 1,
            "output_dir": str(workdir),
            "filename": entry["filename"],
        }

        if args.model:
            request_payload["model"] = args.model

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as req_f:
            json.dump(request_payload, req_f, ensure_ascii=False)
            req_path = req_f.name
        out_json = req_path + ".out"

        backend_cmd = ["python3", str(backend_script),
                       "--request", req_path, "--out-json", out_json]
        if args.config:
            backend_cmd.extend(["--config", args.config])
        if args.alias:
            backend_cmd.extend(["--alias", args.alias])
        elif args.backend:
            backend_cmd.extend(["--backend", args.backend])

        print(f"[dispatch] {entry['illustration_id']} → {entry['filename']}",
              file=sys.stderr)

        attempts = 0
        last_response = None
        while attempts <= args.max_retries:
            attempts += 1
            try:
                proc = subprocess.run(backend_cmd, capture_output=True, text=True, timeout=600)
            except subprocess.TimeoutExpired:
                entry["error"] = {"code": "DISPATCH_TIMEOUT",
                                  "message": "illustration-image-backend invocation exceeded 600s",
                                  "attempts": attempts}
                continue

            if Path(out_json).is_file():
                last_response = json.loads(Path(out_json).read_text(encoding="utf-8"))
            else:
                last_response = {"ok": False, "error": {"code": "NO_OUTPUT",
                                                          "message": (proc.stderr or proc.stdout)[:500]}}

            if last_response.get("ok"):
                images = last_response.get("images") or []
                if not images:
                    entry["error"] = {"code": "EMPTY_RESPONSE",
                                      "message": "backend returned ok but no images",
                                      "attempts": attempts}
                    continue
                first = images[0]
                entry["absolute_path"] = first["path"]
                entry["local_path"] = util.markdown_image_path(
                    Path(first["path"]),
                    Path(mapping["source"]["path"]) if mapping["source"].get("path") else None,
                    mapping["default_output_dir_kind"],
                )
                entry["remote_url"] = first.get("remote_url")
                entry["remote_id"] = first.get("remote_id")
                entry["backend"] = last_response.get("backend")
                entry["model"] = last_response.get("model")
                entry["seed"] = first.get("seed")
                entry["alt_text"] = entry.get("alt_text") or _alt_from_position(entry.get("position", ""))
                entry["status"] = "ok"
                entry.pop("error", None)
                entry["updated_at"] = _now_iso()
                success += 1
                break
            else:
                last_err = last_response.get("error") or {"code": "UNKNOWN", "message": "no error info"}
                entry["error"] = {**last_err, "attempts": attempts}
                if not last_err.get("retryable", False):
                    break

        if entry.get("status") != "ok":
            entry["status"] = "error"
            entry["updated_at"] = _now_iso()
            failed += 1
            err = entry.get("error", {})
            print(f"[dispatch] {entry['illustration_id']} FAILED: {err.get('code')} {err.get('message', '')[:200]}",
                  file=sys.stderr)

        Path(req_path).unlink(missing_ok=True)
        Path(out_json).unlink(missing_ok=True)

        util.write_mapping(workdir, mapping)

    print(f"[dispatch] done: {success} ok, {failed} failed, {skipped} skipped", file=sys.stderr)
    return 0 if failed == 0 else 2


def _parse_outline_frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    out: dict = {}
    for line in text[4:end].splitlines():
        line = line.split("#", 1)[0].rstrip()
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end < 0:
        return text
    return text[end + 5:]


def _aspect_to_size(aspect: str) -> tuple[int, int]:
    table = {
        "1:1": (1024, 1024),
        "16:9": (1536, 1024),
        "9:16": (1024, 1536),
        "4:3": (1408, 1056),
        "3:4": (1056, 1408),
        "3:2": (1408, 939),
        "2.35:1": (1536, 654),
    }
    return table.get(aspect, (1024, 1024))


def _alt_from_position(position: str) -> str:
    parts = position.split("/", 1)
    return (parts[-1].strip() if parts else position)[:120]


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


if __name__ == "__main__":
    sys.exit(main())
