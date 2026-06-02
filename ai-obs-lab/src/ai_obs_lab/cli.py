"""Unified CLI entrypoint.

Usage:
    python -m ai_obs_lab.cli proxy  [--config PATH]
    python -m ai_obs_lab.cli eval   --suite PATH [--repeat N] [--judge] [--logprobs]
    python -m ai_obs_lab.cli report [--date today|YYYY-MM-DD|all] [--out PATH] [--open]
    python -m ai_obs_lab.cli tail   [--log-dir PATH]
    python -m ai_obs_lab.cli version

Phase 2: enable `aolab` console script in pyproject.toml to call `main`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__


def _cmd_proxy(args: argparse.Namespace) -> int:
    from .proxy.server import ProxyConfig, run_proxy
    from .core.store import JSONLStore

    if args.config:
        cfg = ProxyConfig.from_yaml_file(args.config)
    else:
        # Try a few default locations.
        candidates = [
            Path("~/.ai-obs-lab/proxy.yaml").expanduser(),
            Path(__file__).resolve().parent.parent.parent.parent / "config" / "proxy.example.yaml",
        ]
        cfg = None
        for c in candidates:
            if c.exists():
                cfg = ProxyConfig.from_yaml_file(c)
                sys.stderr.write(f"[cli] using config: {c}\n")
                break
        if cfg is None:
            sys.stderr.write("[cli] no config found; using built-in defaults\n")
            cfg = ProxyConfig()
            cfg.upstreams.setdefault("anthropic", "https://api.anthropic.com")
            cfg.upstreams.setdefault("openai", "https://api.openai.com")
    store = JSONLStore(args.log_dir) if args.log_dir else JSONLStore(cfg.log_dir)
    run_proxy(cfg, store=store)
    return 0


def _cmd_eval(args: argparse.Namespace) -> int:
    from .eval.runner import load_suite, run_suite
    from .core.store import JSONLStore

    suite = load_suite(args.suite)
    store = JSONLStore(args.log_dir) if args.log_dir else JSONLStore()
    er = run_suite(
        suite,
        repeat=args.repeat,
        store=store,
        want_logprobs=args.logprobs,
    )
    er.suite_path = str(Path(args.suite).resolve())

    import json as _json
    sys.stdout.write(_json.dumps({
        "eval_run_id": er.eval_run_id,
        "suite": er.suite_name,
        "results": [
            {
                "version": r.version_id,
                "case": r.case_id,
                "similarity_variance": r.similarity_variance,
                "schema_compliance_rate": r.schema_compliance_rate,
                "keyword_hit_rate": r.keyword_hit_rate,
                "avg_logprob_top1": r.avg_logprob_top1,
                "avg_ttft_ms": r.avg_ttft_ms,
                "avg_tokens_out": r.avg_tokens_out,
                "errors": r.errors,
            }
            for r in er.results
        ],
    }, indent=2))
    sys.stdout.write("\n")

    if args.judge:
        from .eval.judge import judge_eval_run
        user_inputs = {c.id: c.user for c in suite.cases}
        judge_eval_run(
            er, store=store,
            judge_model=args.judge_model,
            user_inputs_by_case=user_inputs,
        )
        sys.stderr.write(f"[cli] judge completed for {len(er.results)} (version,case) entries\n")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    from .dashboard.html import main as html_main
    extra = []
    if args.date is not None:
        extra += ["--date", args.date]
    if args.out is not None:
        extra += ["--out", args.out]
    if args.log_dir is not None:
        extra += ["--log-dir", args.log_dir]
    if args.limit is not None:
        extra += ["--limit", str(args.limit)]
    if args.no_inline_details:
        extra += ["--no-inline-details"]
    if args.open:
        extra += ["--open"]
    return html_main(extra)


def _cmd_tail(args: argparse.Namespace) -> int:
    from .dashboard.tail import main as tail_main
    extra = []
    if args.log_dir is not None:
        extra += ["--log-dir", args.log_dir]
    return tail_main(extra)


def _cmd_serve(args: argparse.Namespace) -> int:
    """实时观测看板（常驻 HTTP 服务，浏览器自动刷新）。"""
    from .dashboard.server import run_server
    from .core.store import JSONLStore
    store = JSONLStore(args.log_dir) if args.log_dir else JSONLStore()
    run_server(store, host=args.host, port=args.port, open_browser=args.open)
    return 0


def _cmd_mcp(args: argparse.Namespace) -> int:
    """包一层 stdio MCP server，抓取其 JSON-RPC 交互。

    用法：python -m ai_obs_lab.cli mcp -- <真实 mcp server 命令...>
    """
    from .proxy.mcp_stdio import run_mcp_wrapper
    from .core.store import JSONLStore
    store = JSONLStore(args.log_dir) if args.log_dir else JSONLStore()
    if not args.command:
        sys.stderr.write("[cli] 用法: ai_obs_lab.cli mcp -- <mcp server 命令...>\n")
        return 2
    return run_mcp_wrapper(args.command, store=store, label=args.label)


def _cmd_version(_args: argparse.Namespace) -> int:
    sys.stdout.write(f"ai-obs-lab {__version__}\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ai_obs_lab", description="Local AI observability lab")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("proxy", help="Run the capture proxy")
    sp.add_argument("--config", default=None, help="Path to proxy.yaml")
    sp.add_argument("--log-dir", default=None, help="Override log directory")
    sp.set_defaults(func=_cmd_proxy)

    se = sub.add_parser("eval", help="Run an A/B eval suite")
    se.add_argument("--suite", required=True)
    se.add_argument("--repeat", type=int, default=1)
    se.add_argument("--logprobs", action="store_true")
    se.add_argument("--judge", action="store_true")
    se.add_argument("--judge-model", default="openai:gpt-4o-mini")
    se.add_argument("--log-dir", default=None)
    se.set_defaults(func=_cmd_eval)

    sr = sub.add_parser("report", help="Generate static HTML dashboard")
    sr.add_argument("--date", default="today")
    sr.add_argument("--out", default="~/.ai-obs-lab/report.html")
    sr.add_argument("--log-dir", default=None)
    sr.add_argument("--limit", type=int, default=200)
    sr.add_argument("--no-inline-details", action="store_true")
    sr.add_argument("--open", action="store_true")
    sr.set_defaults(func=_cmd_report)

    st = sub.add_parser("tail", help="Live-tail the trace summary log")
    st.add_argument("--log-dir", default=None)
    st.set_defaults(func=_cmd_tail)

    ss = sub.add_parser("serve", help="实时观测看板（浏览器自动刷新）")
    ss.add_argument("--port", type=int, default=8799)
    ss.add_argument("--host", default="127.0.0.1")
    ss.add_argument("--log-dir", default=None)
    ss.add_argument("--open", action="store_true", help="启动后自动打开浏览器")
    ss.set_defaults(func=_cmd_serve)

    sm = sub.add_parser("mcp", help="包一层 stdio MCP server，抓取 JSON-RPC 交互")
    sm.add_argument("--log-dir", default=None)
    sm.add_argument("--label", default=None, help="会话标签（默认用命令名）")
    sm.add_argument("command", nargs=argparse.REMAINDER,
                    help="-- 之后是真实 mcp server 命令，例如：mcp -- npx some-mcp-server")
    sm.set_defaults(func=_cmd_mcp)

    sv = sub.add_parser("version", help="Print version")
    sv.set_defaults(func=_cmd_version)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
