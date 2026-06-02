#!/usr/bin/env python3
"""Step 7: write generated images back into the source document.

Markdown: directly edits the file (with a .bak backup).
Yuque internal: writes an MCP payload JSON; Claude must execute the call.
Yuque public / text: prints snippets for manual paste.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _setup_imports() -> None:
    here = Path(__file__).resolve().parent
    repo = here.parent
    for p in (here, repo / "adapters", repo / "adapters" / "writeback"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


_setup_imports()

import util  # noqa: E402

import markdown as md_writer          # noqa: E402
import yuque_internal as yi_writer    # noqa: E402
import manual as manual_writer        # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Step 7: insert generated images into the source.")
    p.add_argument("workdir", help="Path to the article workdir.")
    p.add_argument("--yuque-body", help="For yuque_internal: path to a file with the doc body (fetched via MCP).")
    p.add_argument("--out-payload", help="For yuque_internal: where to write the MCP payload JSON.")
    args = p.parse_args()

    workdir = Path(args.workdir).expanduser().resolve()
    mapping = util.load_mapping(workdir)
    if not mapping:
        print(f"error: no .mapping.json in {workdir}", file=sys.stderr)
        return 1

    source_type = mapping["source"]["type"]

    if md_writer.can_handle(source_type):
        article_path = mapping["source"]["path"]
        if not article_path:
            print("error: markdown source has no path in mapping", file=sys.stderr)
            return 1
        result = md_writer.write(article_path, mapping)
        if not result.get("ok"):
            print(f"error: {result.get('error')}", file=sys.stderr)
            return 1
        print(f"[writeback] inserted {len(result['inserted'])} images, appended {len(result['appended'])}",
              file=sys.stderr)
        print(f"[writeback] backup at {result['backup']}", file=sys.stderr)
        for name in result["inserted"]:
            print(f"  ✓ {name}")
        for name in result["appended"]:
            print(f"  ↳ appended (position not found): {name}")
        return 0

    if yi_writer.can_handle(source_type):
        if not args.yuque_body:
            print("error: --yuque-body required for yuque_internal writeback. "
                  "Fetch the doc body via mcp__yuque-mcp__skylark_doc_detail first.",
                  file=sys.stderr)
            return 1
        body = Path(args.yuque_body).expanduser().read_text(encoding="utf-8")
        out_payload = Path(args.out_payload or workdir / "yuque_update_payload.json")
        result = yi_writer.write(
            original_body=body,
            doc_id=mapping["source"].get("doc_id"),
            mapping=mapping,
            payload_out=out_payload,
        )
        print(f"[writeback] yuque_internal payload written to {result['payload_file']}", file=sys.stderr)
        print(f"[writeback] patched {len(result['patched'])} images, "
              f"{len(result['skipped_no_url'])} skipped (no remote_url)", file=sys.stderr)
        for name in result["patched"]:
            print(f"  ✓ {name}")
        for name in result["skipped_no_url"]:
            print(f"  ⚠ no remote_url: {name}")
        print(json.dumps({
            "next_step": "From your Claude session, run:",
            "mcp_tool": result.get("payload_file"),
        }, indent=2))
        return 0

    if manual_writer.can_handle(source_type):
        result = manual_writer.write(mapping)
        print(f"[writeback] {source_type} is not writable from this skill. "
              f"Paste the following snippets manually:", file=sys.stderr)
        for sn in result["snippets"]:
            print(f"\n# at: {sn['position']}")
            print(sn["markdown"])
        return 0

    print(f"error: no writeback adapter for source type {source_type!r}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
