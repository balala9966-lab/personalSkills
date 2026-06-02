#!/usr/bin/env python3
"""One-shot: run all 7 steps (analyze → plan → compose → dispatch → writeback).

Use this when you want the whole flow non-interactively. For step-by-step
review (recommended for first uses), run the individual scripts.

Skips the AskUserQuestion step — relies on CLI args / preferences for choices.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    here = Path(__file__).resolve().parent

    p = argparse.ArgumentParser(description="Run the full composer pipeline end-to-end.")
    p.add_argument("source")
    p.add_argument("--preset", help="Style preset id (e.g. tech-explainer).")
    p.add_argument("--type", dest="type_id")
    p.add_argument("--style", dest="style_id")
    p.add_argument("--palette")
    p.add_argument("--mode", choices=["illustration", "cover", "both"], default="illustration")
    p.add_argument("--aspect", default="16:9")
    p.add_argument("--density", choices=["minimal", "balanced", "per-section", "rich"])
    p.add_argument("--image-count", type=int)
    p.add_argument("--backend")
    p.add_argument("--alias")
    p.add_argument("--model")
    p.add_argument("--config", help="Path to illustration-image-backend backends.yaml.")
    p.add_argument("--language")
    p.add_argument("--prefetched-body")
    p.add_argument("--doc-id")
    p.add_argument("--skip-writeback", action="store_true",
                   help="Stop after dispatch; useful when reviewing images before writeback.")
    args = p.parse_args()

    # Step 1+2: analyze
    analyze_cmd = ["python3", str(here / "analyze.py"), args.source,
                   "--out", "/tmp/composer_analyze.json"]
    if args.prefetched_body:
        analyze_cmd.extend(["--prefetched-body", args.prefetched_body])
    if args.doc_id:
        analyze_cmd.extend(["--doc-id", args.doc_id])
    if _run("analyze", analyze_cmd) != 0:
        return 1
    summary = json.loads(Path("/tmp/composer_analyze.json").read_text())
    workdir = summary["output_dir"]
    print(f"[run] workdir = {workdir}", file=sys.stderr)

    # Step 3+4: plan
    plan_cmd = ["python3", str(here / "plan.py"), workdir,
                "--mode", args.mode, "--aspect", args.aspect]
    if args.preset:
        plan_cmd.extend(["--preset", args.preset])
    if args.type_id:
        plan_cmd.extend(["--type", args.type_id])
    if args.style_id:
        plan_cmd.extend(["--style", args.style_id])
    if args.palette:
        plan_cmd.extend(["--palette", args.palette])
    if args.density:
        plan_cmd.extend(["--density", args.density])
    if args.image_count:
        plan_cmd.extend(["--image-count", str(args.image_count)])
    if args.language:
        plan_cmd.extend(["--language", args.language])
    if _run("plan", plan_cmd) != 0:
        return 1

    # Step 5: compose
    if _run("compose", ["python3", str(here / "compose.py"), workdir]) != 0:
        return 1

    # Step 6: dispatch
    dispatch_cmd = ["python3", str(here / "dispatch.py"), workdir]
    if args.backend:
        dispatch_cmd.extend(["--backend", args.backend])
    if args.alias:
        dispatch_cmd.extend(["--alias", args.alias])
    if args.model:
        dispatch_cmd.extend(["--model", args.model])
    if args.config:
        dispatch_cmd.extend(["--config", args.config])
    dispatch_status = _run("dispatch", dispatch_cmd)

    if args.skip_writeback:
        print("[run] --skip-writeback set; stopping after dispatch", file=sys.stderr)
        return dispatch_status

    # Step 7: writeback
    return _run("writeback", ["python3", str(here / "writeback.py"), workdir])


def _run(label: str, cmd: list[str]) -> int:
    print(f"\n[run] ----- {label} -----", file=sys.stderr)
    print(f"[run] $ {' '.join(cmd)}", file=sys.stderr)
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
