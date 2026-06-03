"""SQLite-backed Store implementation (Phase 2, stdlib-only).

`SQLiteStore` satisfies the same `Store` Protocol as `JSONLStore` but persists
everything into a single SQLite database file. Use it when the per-day JSONL
files grow too large to scan linearly.

Design notes:
- Uses stdlib `sqlite3` only — no third-party dependency, preserving the
  zero-install promise of Phase 1.
- Each model maps to one table; the full nested payload is stored as a JSON
  blob in a `payload` column, while frequently-filtered fields (trace_id,
  ts_start, day) are promoted to real columns + indexes for fast range scans.
- Large request bodies are NOT offloaded to sidecar files here; SQLite handles
  large blobs fine. `request_body_ref` is preserved for round-trip fidelity.
- Thread-safe via a single lock + `check_same_thread=False`. Write volume in
  interactive use is low, so a coarse lock is sufficient.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from .models import EvalRun, JudgeResult, TraceFull, TraceSummary

DEFAULT_DB_PATH = "~/.ai-obs-lab/obs.db"


def _expand(path: str | Path) -> Path:
    return Path(os.path.expanduser(str(path))).resolve()


def _day_str(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def _day_bounds(start: date | None, end: date | None) -> tuple[str | None, str | None]:
    s = start.strftime("%Y-%m-%d") if start else None
    e = end.strftime("%Y-%m-%d") if end else None
    if s and e and s > e:
        s, e = e, s
    return s, e


class SQLiteStore:
    """File-backed Store using a single SQLite database.

    Implements the same contract as `JSONLStore` (see `core.store.Store`).
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = _expand(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS summaries (
                    trace_id TEXT PRIMARY KEY,
                    ts_start REAL NOT NULL,
                    day      TEXT NOT NULL,
                    payload  TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_summaries_day ON summaries(day, ts_start);

                CREATE TABLE IF NOT EXISTS traces (
                    trace_id TEXT PRIMARY KEY,
                    ts_start REAL NOT NULL,
                    day      TEXT NOT NULL,
                    payload  TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS eval_runs (
                    eval_run_id TEXT PRIMARY KEY,
                    ts_start    REAL NOT NULL,
                    day         TEXT NOT NULL,
                    payload     TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_eval_runs_day ON eval_runs(day, ts_start);

                CREATE TABLE IF NOT EXISTS judge_results (
                    judge_id TEXT PRIMARY KEY,
                    ts       REAL NOT NULL,
                    day      TEXT NOT NULL,
                    payload  TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_judge_results_day ON judge_results(day, ts);

                CREATE TABLE IF NOT EXISTS mcp_sessions (
                    session_id TEXT PRIMARY KEY,
                    command    TEXT,
                    label      TEXT,
                    ts_start   REAL,
                    day        TEXT
                );
                CREATE TABLE IF NOT EXISTS mcp_frames (
                    session_id TEXT NOT NULL,
                    ts         REAL NOT NULL,
                    direction  TEXT NOT NULL,
                    method     TEXT,
                    kind       TEXT,
                    payload    TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_mcp_frames_session ON mcp_frames(session_id, ts);
                """
            )
            self._conn.commit()

    # ------------------------------ writers ------------------------------

    def append_summary(self, s: TraceSummary) -> None:
        self._upsert(
            "summaries",
            "trace_id",
            s.trace_id,
            {"ts_start": s.ts_start, "day": _day_str(s.ts_start)},
            s.to_dict(),
        )

    def write_trace(self, t: TraceFull) -> None:
        self._upsert(
            "traces",
            "trace_id",
            t.summary.trace_id,
            {"ts_start": t.summary.ts_start, "day": _day_str(t.summary.ts_start)},
            t.to_dict(),
        )

    def append_eval_run(self, e: EvalRun) -> None:
        self._upsert(
            "eval_runs",
            "eval_run_id",
            e.eval_run_id,
            {"ts_start": e.ts_start, "day": _day_str(e.ts_start)},
            e.to_dict(),
        )

    def append_judge_result(self, j: JudgeResult) -> None:
        ts = j.ts or datetime.now().timestamp()
        self._upsert(
            "judge_results",
            "judge_id",
            j.judge_id,
            {"ts": ts, "day": _day_str(ts)},
            j.to_dict(),
        )

    # --------------------------- stdio MCP -------------------------------

    def write_mcp_meta(
        self, session_id: str, command: str, ts_start: float, *, label: str | None = None
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO mcp_sessions "
                "(session_id, command, label, ts_start, day) VALUES (?,?,?,?,?)",
                (session_id, command, label, ts_start, _day_str(ts_start)),
            )
            self._conn.commit()

    def append_mcp_frame(
        self,
        session_id: str,
        ts: float,
        direction: str,
        payload: dict,
        *,
        method: str | None = None,
        kind: str | None = None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO mcp_frames "
                "(session_id, ts, direction, method, kind, payload) VALUES (?,?,?,?,?,?)",
                (session_id, ts, direction, method, kind,
                 json.dumps(payload, ensure_ascii=False)),
            )
            self._conn.commit()

    # ------------------------------ readers ------------------------------

    def iter_summaries(
        self, start: date | None = None, end: date | None = None
    ) -> Iterator[TraceSummary]:
        for row in self._iter_rows("summaries", "ts_start", start, end):
            yield TraceSummary.from_dict(json.loads(row["payload"]))

    def load_trace(self, trace_id: str, ts: float | None = None) -> TraceFull:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM traces WHERE trace_id = ?", (trace_id,)
            ).fetchone()
        if row is None:
            raise FileNotFoundError(f"trace not found: {trace_id}")
        return TraceFull.from_dict(json.loads(row["payload"]))

    def iter_eval_runs(
        self, start: date | None = None, end: date | None = None
    ) -> Iterator[EvalRun]:
        for row in self._iter_rows("eval_runs", "ts_start", start, end):
            yield EvalRun.from_dict(json.loads(row["payload"]))

    def iter_judge_results(
        self, start: date | None = None, end: date | None = None
    ) -> Iterator[JudgeResult]:
        for row in self._iter_rows("judge_results", "ts", start, end):
            yield JudgeResult.from_dict(json.loads(row["payload"]))

    def iter_mcp_sessions(
        self, start: date | None = None, end: date | None = None
    ) -> Iterator[dict]:
        s, e = _day_bounds(start, end)
        clause, params = self._day_clause(s, e)
        with self._lock:
            sessions = self._conn.execute(
                f"SELECT session_id, command, label, ts_start FROM mcp_sessions "
                f"{clause} ORDER BY ts_start DESC",
                params,
            ).fetchall()
            result: list[dict] = []
            for sess in sessions:
                frames = self._conn.execute(
                    "SELECT ts, direction, method, kind, payload FROM mcp_frames "
                    "WHERE session_id = ? ORDER BY ts ASC",
                    (sess["session_id"],),
                ).fetchall()
                result.append({
                    "session_id": sess["session_id"],
                    "command": sess["command"] or "",
                    "label": sess["label"],
                    "ts_start": sess["ts_start"],
                    "frames": [
                        {
                            "ts": f["ts"],
                            "direction": f["direction"],
                            "method": f["method"],
                            "kind": f["kind"],
                            "payload": json.loads(f["payload"]),
                        }
                        for f in frames
                    ],
                })
        yield from result

    # ------------------------------ migration ----------------------------

    @classmethod
    def from_jsonl(
        cls, jsonl_base_dir: str | Path, db_path: str | Path = DEFAULT_DB_PATH
    ) -> "SQLiteStore":
        """Import an existing JSONLStore directory into a new SQLiteStore.

        Reads every summary / trace / eval_run / judge_result / mcp session from
        the JSONL layout and writes it into the SQLite database, then returns the
        populated store. Idempotent: re-running upserts by primary key.
        """
        from .store import JSONLStore

        src = JSONLStore(jsonl_base_dir)
        store = cls(db_path)
        for summary in src.iter_summaries():
            store.append_summary(summary)
            try:
                store.write_trace(src.load_trace(summary.trace_id, ts=summary.ts_start))
            except FileNotFoundError:
                pass
        for run in src.iter_eval_runs():
            store.append_eval_run(run)
        for judge in src.iter_judge_results():
            store.append_judge_result(judge)
        for session in src.iter_mcp_sessions():
            store.write_mcp_meta(
                session["session_id"],
                session["command"],
                session.get("ts_start") or 0.0,
                label=session.get("label"),
            )
            for frame in session["frames"]:
                store.append_mcp_frame(
                    session["session_id"],
                    frame.get("ts") or 0.0,
                    frame.get("direction", ""),
                    frame.get("payload") or {},
                    method=frame.get("method"),
                    kind=frame.get("kind"),
                )
        return store

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ------------------------------ helpers ------------------------------

    def _upsert(
        self, table: str, key_col: str, key_val: str, cols: dict, payload: dict
    ) -> None:
        col_names = [key_col, *cols.keys(), "payload"]
        placeholders = ",".join("?" for _ in col_names)
        values = [key_val, *cols.values(), json.dumps(payload, ensure_ascii=False)]
        with self._lock:
            self._conn.execute(
                f"INSERT OR REPLACE INTO {table} ({','.join(col_names)}) "
                f"VALUES ({placeholders})",
                values,
            )
            self._conn.commit()

    @staticmethod
    def _day_clause(s: str | None, e: str | None) -> tuple[str, list]:
        if s is None and e is None:
            return "", []
        if s is not None and e is not None:
            return "WHERE day >= ? AND day <= ?", [s, e]
        if s is not None:
            return "WHERE day >= ?", [s]
        return "WHERE day <= ?", [e]

    def _iter_rows(
        self, table: str, order_col: str, start: date | None, end: date | None
    ) -> list[sqlite3.Row]:
        s, e = _day_bounds(start, end)
        clause, params = self._day_clause(s, e)
        with self._lock:
            return self._conn.execute(
                f"SELECT payload FROM {table} {clause} ORDER BY {order_col} ASC",
                params,
            ).fetchall()
