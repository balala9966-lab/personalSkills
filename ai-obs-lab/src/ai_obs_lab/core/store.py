"""Storage layer.

Defines the abstract `Store` Protocol and the default `JSONLStore` implementation
that persists everything as JSONL + per-trace JSON files on local disk.

Phase 2 may add a DuckDBStore / SQLiteStore — the Protocol is the contract.

Layout (default base = ~/.ai-obs-lab/logs):

    base/
      YYYY-MM-DD/
        summary.jsonl              # one TraceSummary per line
        eval_runs.jsonl            # one EvalRun per line
        judge_results.jsonl        # one JudgeResult per line
        traces/<trace_id>.json     # one TraceFull per file
        traces/<trace_id>.body.json  # sidecar request_body when >256KB
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Iterator, Protocol

from .models import EvalRun, JudgeResult, TraceFull, TraceSummary

DEFAULT_BASE_DIR = "~/.ai-obs-lab/logs"
LARGE_BODY_BYTES = 256 * 1024  # 256KB threshold


def _expand(path: str | Path) -> Path:
    return Path(os.path.expanduser(str(path))).resolve()


def _day_dir(base: Path, ts: float) -> Path:
    d = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    return base / d


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class Store(Protocol):
    def append_summary(self, s: TraceSummary) -> None: ...
    def write_trace(self, t: TraceFull) -> None: ...
    def iter_summaries(
        self, start: date | None = None, end: date | None = None
    ) -> Iterator[TraceSummary]: ...
    def load_trace(self, trace_id: str, ts: float | None = None) -> TraceFull: ...
    def append_eval_run(self, e: EvalRun) -> None: ...
    def iter_eval_runs(
        self, start: date | None = None, end: date | None = None
    ) -> Iterator[EvalRun]: ...
    def append_judge_result(self, j: JudgeResult) -> None: ...
    def iter_judge_results(
        self, start: date | None = None, end: date | None = None
    ) -> Iterator[JudgeResult]: ...


# ---------------------------------------------------------------------------
# JSONL implementation
# ---------------------------------------------------------------------------


class JSONLStore:
    """File-backed Store. Thread-safe via a single coarse lock per file kind.

    Designed for low write volume (a few hundred traces / day in interactive
    use). For high-throughput scenarios, switch to a DB-backed Store in Phase 2.
    """

    def __init__(self, base_dir: str | Path = DEFAULT_BASE_DIR) -> None:
        self.base_dir = _expand(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    # ------------------------------ writers ------------------------------

    def append_summary(self, s: TraceSummary) -> None:
        day = _day_dir(self.base_dir, s.ts_start)
        day.mkdir(parents=True, exist_ok=True)
        self._append_jsonl(day / "summary.jsonl", s.to_dict())

    def write_trace(self, t: TraceFull) -> None:
        day = _day_dir(self.base_dir, t.summary.ts_start)
        traces_dir = day / "traces"
        traces_dir.mkdir(parents=True, exist_ok=True)

        # Offload large request bodies to a sidecar file.
        body = t.request_body
        ref = t.request_body_ref
        if body is not None:
            body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
            if len(body_bytes) > LARGE_BODY_BYTES:
                sidecar = traces_dir / f"{t.summary.trace_id}.body.json"
                sidecar.write_bytes(body_bytes)
                ref = str(sidecar.relative_to(self.base_dir))
                body = None

        payload = TraceFull(
            summary=t.summary,
            request_headers=t.request_headers,
            request_body=body,
            request_body_ref=ref,
            response_headers=t.response_headers,
            response_text=t.response_text,
            chunks=t.chunks,
            tool_calls=t.tool_calls,
            pauses_ms=t.pauses_ms,
        ).to_dict()

        target = traces_dir / f"{t.summary.trace_id}.json"
        with self._lock:
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    def append_eval_run(self, e: EvalRun) -> None:
        day = _day_dir(self.base_dir, e.ts_start)
        day.mkdir(parents=True, exist_ok=True)
        self._append_jsonl(day / "eval_runs.jsonl", e.to_dict())

    def append_judge_result(self, j: JudgeResult) -> None:
        ts = j.ts or datetime.now().timestamp()
        day = _day_dir(self.base_dir, ts)
        day.mkdir(parents=True, exist_ok=True)
        self._append_jsonl(day / "judge_results.jsonl", j.to_dict())

    # ------------------------------ readers ------------------------------

    def iter_summaries(
        self, start: date | None = None, end: date | None = None
    ) -> Iterator[TraceSummary]:
        for d in self._iter_day_dirs(start, end):
            path = d / "summary.jsonl"
            if not path.exists():
                continue
            for obj in self._read_jsonl(path):
                yield TraceSummary.from_dict(obj)

    def load_trace(self, trace_id: str, ts: float | None = None) -> TraceFull:
        # If timestamp hint provided, look in that day first; else scan recent days.
        candidates: list[Path] = []
        if ts is not None:
            candidates.append(_day_dir(self.base_dir, ts) / "traces" / f"{trace_id}.json")
        # Fallback: scan all day dirs (sorted descending for recency-first).
        for d in sorted(self._all_day_dirs(), reverse=True):
            candidates.append(d / "traces" / f"{trace_id}.json")

        for path in candidates:
            if path.exists():
                data = json.loads(path.read_text())
                tf = TraceFull.from_dict(data)
                # Hydrate sidecar body if present.
                if tf.request_body is None and tf.request_body_ref:
                    sidecar = self.base_dir / tf.request_body_ref
                    if sidecar.exists():
                        tf.request_body = json.loads(sidecar.read_text())
                return tf
        raise FileNotFoundError(f"trace not found: {trace_id}")

    def iter_eval_runs(
        self, start: date | None = None, end: date | None = None
    ) -> Iterator[EvalRun]:
        for d in self._iter_day_dirs(start, end):
            path = d / "eval_runs.jsonl"
            if not path.exists():
                continue
            for obj in self._read_jsonl(path):
                yield EvalRun.from_dict(obj)

    def iter_judge_results(
        self, start: date | None = None, end: date | None = None
    ) -> Iterator[JudgeResult]:
        for d in self._iter_day_dirs(start, end):
            path = d / "judge_results.jsonl"
            if not path.exists():
                continue
            for obj in self._read_jsonl(path):
                yield JudgeResult.from_dict(obj)

    # ------------------------------ helpers ------------------------------

    def _append_jsonl(self, path: Path, obj: dict) -> None:
        line = json.dumps(obj, ensure_ascii=False)
        with self._lock:
            with path.open("a", encoding="utf-8") as f:
                f.write(line)
                f.write("\n")

    @staticmethod
    def _read_jsonl(path: Path) -> Iterable[dict]:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    # Skip malformed lines instead of aborting iteration.
                    continue

    def _all_day_dirs(self) -> list[Path]:
        if not self.base_dir.exists():
            return []
        return [
            p for p in self.base_dir.iterdir()
            if p.is_dir() and len(p.name) == 10 and p.name[4] == "-" and p.name[7] == "-"
        ]

    def _iter_day_dirs(
        self, start: date | None, end: date | None
    ) -> Iterator[Path]:
        if start is None and end is None:
            yield from sorted(self._all_day_dirs())
            return
        # Inclusive range; default missing side to today.
        today = date.today()
        s = start or today
        e = end or today
        if s > e:
            s, e = e, s
        cur = s
        while cur <= e:
            d = self.base_dir / cur.strftime("%Y-%m-%d")
            if d.exists():
                yield d
            cur = cur + timedelta(days=1)
