"""Dataclasses for traces, eval runs, and judge results.

All models are JSON-serializable via `to_dict` / `from_dict`. We deliberately
avoid third-party libraries (no pydantic) to keep Phase 1 stdlib-only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Trace models
# ---------------------------------------------------------------------------


@dataclass
class Chunk:
    """A single SSE chunk delta with timing information."""

    seq: int
    ts_offset_ms: float  # ms since request start
    kind: str            # "text" | "tool_use" | "tool_args" | "stop" | "pause" | "other"
    text: str = ""
    tool_id: str = ""
    raw_event: str = ""  # event type name from SSE, for debugging


@dataclass
class ToolCallRecord:
    """An aggregated tool call extracted from streaming chunks."""

    tool_id: str
    name: str
    arguments_json: str  # raw string; may or may not parse as JSON
    parsed_ok: bool = False


@dataclass
class TraceSummary:
    """One-line summary stored in summary.jsonl for fast scanning."""

    trace_id: str
    ts_start: float
    client_hint: str             # claude-code / codex / cfuse / unknown
    upstream: str                # anthropic / openai / <profile>
    method: str
    path: str
    model: str | None = None
    status: int | None = None
    ttft_ms: float | None = None
    total_ms: float | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    chunks: int | None = None
    tool_call_count: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TraceSummary":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})


@dataclass
class TraceFull:
    """Full trace: request + response + chunk timeline + extracted tool calls."""

    summary: TraceSummary
    request_headers: dict[str, Any] = field(default_factory=dict)
    request_body: dict[str, Any] | None = None
    request_body_ref: str | None = None  # sidecar path if body offloaded
    response_headers: dict[str, Any] = field(default_factory=dict)
    response_text: str = ""              # concatenated text deltas
    chunks: list[Chunk] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    pauses_ms: list[float] = field(default_factory=list)  # gap durations of pause events

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary.to_dict(),
            "request_headers": self.request_headers,
            "request_body": self.request_body,
            "request_body_ref": self.request_body_ref,
            "response_headers": self.response_headers,
            "response_text": self.response_text,
            "chunks": [asdict(c) for c in self.chunks],
            "tool_calls": [asdict(t) for t in self.tool_calls],
            "pauses_ms": self.pauses_ms,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TraceFull":
        return cls(
            summary=TraceSummary.from_dict(d["summary"]),
            request_headers=d.get("request_headers") or {},
            request_body=d.get("request_body"),
            request_body_ref=d.get("request_body_ref"),
            response_headers=d.get("response_headers") or {},
            response_text=d.get("response_text", ""),
            chunks=[Chunk(**c) for c in (d.get("chunks") or [])],
            tool_calls=[ToolCallRecord(**t) for t in (d.get("tool_calls") or [])],
            pauses_ms=list(d.get("pauses_ms") or []),
        )


# ---------------------------------------------------------------------------
# Eval models
# ---------------------------------------------------------------------------


@dataclass
class EvalCaseResult:
    """Aggregated metrics for one (version, case) pair across N repeats."""

    version_id: str
    case_id: str
    repeats: int
    trace_ids: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    similarity_variance: float | None = None      # 1 - mean pairwise SequenceMatcher ratio
    schema_compliance_rate: float | None = None   # 0..1
    keyword_hit_rate: float | None = None         # 0..1
    avg_logprob_top1: float | None = None         # 0..1
    avg_ttft_ms: float | None = None
    avg_total_ms: float | None = None
    avg_tokens_out: float | None = None
    errors: int = 0


@dataclass
class EvalRun:
    """One execution of a suite (one row in eval_runs.jsonl)."""

    eval_run_id: str
    ts_start: float
    suite_name: str
    suite_path: str
    upstream: str
    model: str
    temperature: float
    repeat: int
    version_ids: list[str] = field(default_factory=list)
    case_ids: list[str] = field(default_factory=list)
    results: list[EvalCaseResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Ensure nested dataclasses serialize cleanly (asdict already handles this).
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EvalRun":
        results = [EvalCaseResult(**r) for r in (d.get("results") or [])]
        d2 = {k: v for k, v in d.items() if k != "results"}
        return cls(results=results, **d2)


# ---------------------------------------------------------------------------
# Judge models
# ---------------------------------------------------------------------------


@dataclass
class JudgeResult:
    """LLM-as-Judge score for one trace (or one eval output)."""

    judge_id: str
    trace_id: str
    eval_run_id: str | None
    version_id: str | None
    case_id: str | None
    judge_model: str
    rubric: dict[str, int]   # {correctness: 1-5, format: 1-5, conciseness: 1-5, faithfulness: 1-5}
    overall: float
    rationale: str = ""
    ts: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "JudgeResult":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})
