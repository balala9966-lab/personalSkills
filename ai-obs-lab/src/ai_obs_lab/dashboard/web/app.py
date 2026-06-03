"""FastAPI Web UI backend (Phase 2, optional dependency).

This is a thin FastAPI layer over the SAME pure data functions used by the
stdlib `dashboard/server.py`. It serves identical endpoints so the existing
front-end (`_LIVE_HTML`) works unchanged:

    GET /                        dashboard HTML (polling JS)
    GET /api/snapshot?date=...   overview + lightweight trace list
    GET /api/trace/<id>?ts=...   one TraceFull + parsed context
    GET /_health                 health check

FastAPI/uvicorn are OPTIONAL. They are imported lazily inside `build_app` /
`run_server` so that importing this module never fails on a stdlib-only install.
Callers (cli `serve --backend fastapi`) must handle ImportError and fall back to
the stdlib server.
"""

from __future__ import annotations

from dataclasses import asdict

from ...core.store import JSONLStore
from .. import query as Q
from ..html import _resolve_range
from ..server import _LIVE_HTML, _safe_mcp_sessions


def fastapi_available() -> bool:
    """True if FastAPI (and a server to run it) can be imported."""
    try:
        import fastapi  # noqa: F401
        return True
    except ImportError:
        return False


def _snapshot_payload(store: JSONLStore, date_spec: str) -> dict:
    start, end = _resolve_range(date_spec)
    summaries = Q.list_traces(store, start=start, end=end, limit=300)
    return {
        "overview": Q.trace_overview(summaries),
        "traces": [asdict(s) for s in summaries],
        "tools": Q.aggregate_tool_calls(store, start=start, end=end),
        "mcp_sessions": _safe_mcp_sessions(store, start, end),
    }


def _trace_payload(store: JSONLStore, trace_id: str, ts: float | None) -> dict:
    tf = store.load_trace(trace_id, ts=ts)
    d = tf.to_dict()
    d["context"] = Q.parse_request_context(d.get("request_body"))
    return d


def build_app(store: JSONLStore):
    """Construct a FastAPI app wired to the given store.

    Raises ImportError if FastAPI is not installed — callers must catch it and
    fall back to the stdlib server.
    """
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

    app = FastAPI(title="ai-obs-lab", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    @app.get("/index.html", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return HTMLResponse(_LIVE_HTML)

    @app.get("/_health", response_class=PlainTextResponse)
    def health() -> PlainTextResponse:
        return PlainTextResponse("ok")

    @app.get("/api/snapshot")
    def snapshot(date: str = Query("today")) -> JSONResponse:
        try:
            return JSONResponse(_snapshot_payload(store, date))
        except Exception as e:
            return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)

    @app.get("/api/trace/{trace_id}")
    def trace(trace_id: str, ts: float | None = Query(None)) -> JSONResponse:
        try:
            return JSONResponse(_trace_payload(store, trace_id, ts))
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="trace not found")
        except Exception as e:
            return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)

    return app


def run_server(
    store: JSONLStore,
    *,
    host: str = "127.0.0.1",
    port: int = 8799,
    open_browser: bool = False,
) -> None:
    """Run the FastAPI app via uvicorn. Raises ImportError if deps missing."""
    import uvicorn

    app = build_app(store)
    if open_browser:
        import threading
        import time
        import webbrowser

        def _open() -> None:
            time.sleep(0.6)
            webbrowser.open(f"http://{host}:{port}")

        threading.Thread(target=_open, daemon=True).start()
    uvicorn.run(app, host=host, port=port, log_level="warning")