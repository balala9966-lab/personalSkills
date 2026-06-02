"""Terminal `tail -f` for the latest summary.jsonl.

Polls the current day's summary file every 0.5s and pretty-prints any new
TraceSummary rows. Handles day rollover automatically.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path

from ..core.store import JSONLStore


def _day_path(base: Path, d: date) -> Path:
    return base / d.strftime("%Y-%m-%d") / "summary.jsonl"


def _fmt(d: dict) -> str:
    ts = d.get("ts_start")
    when = datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "--:--:--"
    client = (d.get("client_hint") or "?")[:14].ljust(14)
    upstream = (d.get("upstream") or "?")[:10].ljust(10)
    status = str(d.get("status") or "-").rjust(3)
    model = (d.get("model") or "-")[:24].ljust(24)
    ttft = d.get("ttft_ms")
    ttft_s = f"{ttft:>6.0f}ms" if isinstance(ttft, (int, float)) else "     -"
    total = d.get("total_ms")
    total_s = f"{total:>7.0f}ms" if isinstance(total, (int, float)) else "      -"
    tin = d.get("tokens_in") or "-"
    tout = d.get("tokens_out") or "-"
    tools = d.get("tool_call_count") or 0
    path = (d.get("path") or "")[:50]
    err = d.get("error")
    tail = f" ⚠ {err}" if err else ""
    return (f"{when} {client} {upstream} {status} {model} "
            f"ttft={ttft_s} total={total_s} tok={tin}/{tout} tools={tools} {path}{tail}")


def tail_loop(store: JSONLStore, *, follow: bool = True, sleep_s: float = 0.5) -> None:
    base = store.base_dir
    cur_day = date.today()
    path = _day_path(base, cur_day)
    offset = 0
    # Don't replay history on startup — start from end of file.
    if path.exists():
        offset = path.stat().st_size
    sys.stderr.write(f"[ai-obs-lab tail] watching {path}\n")
    try:
        while True:
            today = date.today()
            if today != cur_day:
                cur_day = today
                path = _day_path(base, cur_day)
                offset = 0
                sys.stderr.write(f"[ai-obs-lab tail] day rolled over → {path}\n")
            if path.exists():
                size = path.stat().st_size
                if size < offset:
                    # File was truncated/rotated; rewind.
                    offset = 0
                if size > offset:
                    with path.open("rb") as f:
                        f.seek(offset)
                        chunk = f.read(size - offset)
                        offset = size
                    for line in chunk.decode("utf-8", errors="replace").splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            d = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        sys.stdout.write(_fmt(d) + "\n")
                        sys.stdout.flush()
            if not follow:
                return
            time.sleep(sleep_s)
    except KeyboardInterrupt:
        sys.stderr.write("\n[ai-obs-lab tail] stopped\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ai_obs_lab.dashboard.tail")
    p.add_argument("--log-dir", default=None)
    p.add_argument("--no-follow", action="store_true")
    args = p.parse_args(argv)
    store = JSONLStore(args.log_dir) if args.log_dir else JSONLStore()
    tail_loop(store, follow=not args.no_follow)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
