"""实时观测看板 —— 轻量 HTTP 服务（stdlib only）。

与静态报告（html.py）的区别：这是一个常驻服务，浏览器打开后每隔几秒自动
向 /api/snapshot 拉取最新数据，新请求自动出现在表格顶部并高亮。点击某条
trace 时再按需向 /api/trace/<id> 拉取详情（含上下文面板），避免一次性把所有
trace 的完整 body 都塞进页面。

复用 dashboard/query.py 的纯数据层，不重复造轮子。

路由：
    GET /                        看板 HTML（含轮询 JS）
    GET /api/snapshot?date=today 概览 + trace 列表（轻量，不含每条 body）
    GET /api/trace/<id>?ts=<ts>  单条 TraceFull + 上下文解析（按需懒加载）
    GET /_health                 健康检查
"""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

from ..core.store import JSONLStore
from . import query as Q
from .html import _resolve_range  # 复用日期范围解析


DEFAULT_PORT = 8799


def _make_handler(store: JSONLStore):
    class LiveHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:  # 静默逐请求日志
            pass

        def do_GET(self) -> None:  # noqa: N802
            parts = urlsplit(self.path)
            path = parts.path
            qs = parse_qs(parts.query)
            if path == "/" or path == "/index.html":
                self._send_html(_LIVE_HTML)
                return
            if path == "/_health":
                self._send_text(200, "ok")
                return
            if path == "/api/snapshot":
                self._api_snapshot(qs)
                return
            if path.startswith("/api/trace/"):
                self._api_trace(path[len("/api/trace/"):], qs)
                return
            self._send_text(404, "not found")

        # ---------- API ----------

        def _api_snapshot(self, qs: dict) -> None:
            date_spec = (qs.get("date") or ["today"])[0]
            start, end = _resolve_range(date_spec)
            try:
                # 实时看板只要轻量列表 + 概览，不内联每条 body（详情走 /api/trace）。
                summaries = Q.list_traces(store, start=start, end=end, limit=300)
                from dataclasses import asdict
                payload = {
                    "overview": Q.trace_overview(summaries),
                    "traces": [asdict(s) for s in summaries],
                    "tools": Q.aggregate_tool_calls(store, start=start, end=end),
                    "mcp_sessions": _safe_mcp_sessions(store, start, end),
                }
                self._send_json(payload)
            except Exception as e:
                self._send_json({"error": f"{type(e).__name__}: {e}"}, status=500)

        def _api_trace(self, trace_id: str, qs: dict) -> None:
            ts_raw = (qs.get("ts") or [None])[0]
            ts = float(ts_raw) if ts_raw else None
            try:
                tf = store.load_trace(trace_id, ts=ts)
                d = tf.to_dict()
                d["context"] = Q.parse_request_context(d.get("request_body"))
                self._send_json(d)
            except FileNotFoundError:
                self._send_json({"error": "trace not found"}, status=404)
            except Exception as e:
                self._send_json({"error": f"{type(e).__name__}: {e}"}, status=500)

        # ---------- io ----------

        def _send_json(self, obj: dict, status: int = 200) -> None:
            body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, status: int, text: str) -> None:
            body = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return LiveHandler


def _safe_mcp_sessions(store: JSONLStore, start, end) -> list:
    """stdio MCP 会话（组件 2 落盘的数据）。该能力未就绪时安全返回空列表。"""
    fn = getattr(store, "iter_mcp_sessions", None)
    if not callable(fn):
        return []
    try:
        return list(fn(start=start, end=end))
    except Exception:
        return []


class _ThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def run_server(store: JSONLStore, *, host: str = "127.0.0.1",
               port: int = DEFAULT_PORT, open_browser: bool = False) -> None:
    handler = _make_handler(store)
    server = _ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}"
    sys.stderr.write(
        f"[ai-obs-lab] 实时看板已启动：{url}\n"
        f"             日志目录 = {store.base_dir}\n"
        f"             按 Ctrl-C 停止\n"
    )
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("\n[ai-obs-lab] 看板已停止\n")
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ai_obs_lab.dashboard.server")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--log-dir", default=None)
    p.add_argument("--open", action="store_true")
    args = p.parse_args(argv)
    store = JSONLStore(args.log_dir) if args.log_dir else JSONLStore()
    run_server(store, host=args.host, port=args.port, open_browser=args.open)
    return 0


# ---------------------------------------------------------------------------
# 看板 HTML（占位，前端 JS 在下一步补全）
# ---------------------------------------------------------------------------

_LIVE_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>AI 观测实验台 · 实时看板</title>
<style>
  :root {
    --bg: #0f1115; --fg: #e6e6e6; --muted: #9aa3af; --card: #161a22;
    --accent: #6ea8fe; --warn: #f4b860; --err: #ef6a6a; --ok: #79d18a;
    --border: #2a313c;
  }
  html, body { background: var(--bg); color: var(--fg);
    font: 13px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", monospace; margin: 0; }
  header { padding: 12px 20px; border-bottom: 1px solid var(--border); display: flex; gap: 16px; align-items: center; }
  header h1 { margin: 0; font-size: 16px; }
  header .meta { color: var(--muted); font-size: 12px; }
  header .live-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--ok); display: inline-block; margin-right: 4px; animation: pulse 1.6s infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }
  nav { display: flex; gap: 8px; padding: 8px 20px; border-bottom: 1px solid var(--border); align-items: center; }
  nav button { background: var(--card); color: var(--fg); border: 1px solid var(--border);
    padding: 6px 12px; border-radius: 4px; cursor: pointer; font: inherit; }
  nav button.active { border-color: var(--accent); color: var(--accent); }
  nav .spacer { flex: 1; }
  nav label { color: var(--muted); font-size: 12px; }
  main { padding: 16px 20px; }
  .grid.kpi { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 12px; }
  .card h3 { margin: 0 0 6px; font-size: 12px; color: var(--muted); font-weight: 500; }
  .card .v { font-size: 20px; font-weight: 600; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th, td { padding: 6px 10px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }
  th { color: var(--muted); font-weight: 500; background: rgba(255,255,255,0.02); position: sticky; top: 0; }
  tr.row-link { cursor: pointer; }
  tr.row-link:hover { background: rgba(110,168,254,0.08); }
  tr.row-link.selected { background: rgba(110,168,254,0.14); }
  @keyframes flashin { from { background: rgba(121,209,138,0.35); } to { background: transparent; } }
  tr.flash { animation: flashin 2.2s ease-out; }
  .status-ok { color: var(--ok); }
  .status-err { color: var(--err); }
  .badge { display: inline-block; padding: 1px 6px; border-radius: 3px; background: rgba(255,255,255,0.06); font-size: 11px; }
  .panel { display: none; }
  .panel.active { display: block; }
  .detail { background: var(--card); border: 1px solid var(--border); border-radius: 6px;
    padding: 12px; margin-top: 12px; max-height: 70vh; overflow: auto; }
  .detail h4 { margin: 12px 0 4px; color: var(--accent); font-size: 12px; }
  pre { background: rgba(0,0,0,0.3); padding: 8px; border-radius: 4px; overflow: auto;
    white-space: pre-wrap; word-break: break-word; font-size: 12px; }
  .chunks { display: flex; flex-wrap: wrap; gap: 4px; }
  .chunk { padding: 2px 6px; border-radius: 3px; font-size: 11px; border: 1px solid var(--border); }
  .chunk.text { background: rgba(121,209,138,0.10); }
  .chunk.tool_use { background: rgba(110,168,254,0.15); }
  .chunk.tool_args { background: rgba(110,168,254,0.08); }
  .chunk.stop { background: rgba(154,163,175,0.15); }
  .chunk.pause { background: rgba(244,184,96,0.20); color: var(--warn); font-weight: bold; }
  details { margin: 4px 0; }
  details summary { cursor: pointer; color: var(--muted); }
  .empty { padding: 20px; text-align: center; color: var(--muted); }
  .small { color: var(--muted); font-size: 11px; }
  .number { text-align: right; font-variant-numeric: tabular-nums; }
  .ctxbar { display: flex; height: 14px; border-radius: 4px; overflow: hidden; margin: 4px 0; border: 1px solid var(--border); }
  .ctxbar .seg { height: 100%; }
  .seg-sys { background: #c084fc; } .seg-tool { background: var(--accent); } .seg-msg { background: var(--ok); }
  .dot { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 2px; }
  .dot-sys { background: #c084fc; } .dot-tool { background: var(--accent); } .dot-msg { background: var(--ok); }
  .badge-MCP { background: rgba(110,168,254,0.25); color: var(--accent); }
  .badge-skill { background: rgba(192,132,252,0.25); color: #c084fc; }
  .badge-builtin { background: rgba(154,163,175,0.2); }
  .badge-role-user { background: rgba(121,209,138,0.18); color: var(--ok); }
  .badge-role-assistant { background: rgba(110,168,254,0.18); color: var(--accent); }
</style>
</head>
<body>
<header>
  <h1>AI 观测实验台</h1>
  <span class="meta"><span class="live-dot"></span>实时看板 · 每 <span id="interval">3</span> 秒自动刷新 · 最后更新 <span id="last-update">—</span></span>
</header>
<nav>
  <button data-tab="traces" class="active">请求追踪</button>
  <button data-tab="tools">工具与 MCP</button>
  <span class="spacer"></span>
  <label>日期范围：</label>
  <select id="date-sel">
    <option value="today">今天</option>
    <option value="yesterday">昨天</option>
    <option value="all">全部</option>
  </select>
  <label><input type="checkbox" id="autorefresh" checked /> 自动刷新</label>
</nav>
<main>
  <section id="tab-traces" class="panel active">
    <div class="grid kpi" id="kpis"></div>
    <div class="card" style="margin-top:12px">
      <h3>最近请求（点击行查看完整上下文）</h3>
      <div style="max-height: 55vh; overflow: auto">
        <table id="traces-table">
          <thead><tr>
            <th>时间</th><th>客户端</th><th>上游</th><th>模型</th>
            <th>状态</th><th class="number">首字延迟</th><th class="number">总耗时</th>
            <th class="number">token 入/出</th><th class="number">工具数</th><th>路径</th>
          </tr></thead>
          <tbody></tbody>
        </table>
      </div>
      <div id="trace-detail"></div>
    </div>
  </section>
  <section id="tab-tools" class="panel">
    <div id="tools-root"></div>
    <div id="mcp-root" style="margin-top:16px"></div>
  </section>
</main>
<script>
// ---- 工具函数 ----
function esc(s){ if(s==null) return ""; return String(s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }
function fmtTs(ts){ if(!ts) return ""; return new Date(ts*1000).toLocaleTimeString(); }
function fmtMs(v){ return v==null?"—":(v<1000?v.toFixed(0)+"ms":(v/1000).toFixed(2)+"s"); }
function fmtNum(v){ return v==null?"—":String(v); }

let STATE = { traces: [], overview: {}, tools: {}, mcp: [], selected: null, knownIds: new Set() };

// ---- 拉取快照（轮询）----
async function poll(){
  const dateSpec = document.getElementById("date-sel").value;
  try{
    const r = await fetch("/api/snapshot?date=" + encodeURIComponent(dateSpec), {cache:"no-store"});
    const data = await r.json();
    if(data.error){ console.warn(data.error); return; }
    applySnapshot(data);
    document.getElementById("last-update").textContent = new Date().toLocaleTimeString();
  }catch(e){ console.warn("轮询失败", e); }
}

function applySnapshot(data){
  // 找出新增的 trace（用于高亮）
  const newIds = new Set();
  (data.traces||[]).forEach(t => { if(!STATE.knownIds.has(t.trace_id)) newIds.add(t.trace_id); });
  STATE.traces = data.traces||[];
  STATE.overview = data.overview||{};
  STATE.tools = data.tools||{};
  STATE.mcp = data.mcp_sessions||[];
  STATE.traces.forEach(t => STATE.knownIds.add(t.trace_id));
  renderKPIs();
  renderTraces(newIds);
  renderTools();
  renderMcp();
}

function renderKPIs(){
  const o = STATE.overview||{};
  const cards = [
    ["总请求数", o.total ?? 0],
    ["错误数", o.errors ?? 0],
    ["平均首字延迟", fmtMs(o.avg_ttft_ms)],
    ["token 输入", o.tokens_in_total ?? 0],
    ["token 输出", o.tokens_out_total ?? 0],
    ["工具调用次数", o.tool_call_total ?? 0],
  ];
  document.getElementById("kpis").innerHTML = cards.map(
    ([k,v]) => `<div class="card"><h3>${esc(k)}</h3><div class="v">${esc(v)}</div></div>`
  ).join("");
}

function renderTraces(newIds){
  const tbody = document.querySelector("#traces-table tbody");
  if(!STATE.traces.length){
    tbody.innerHTML = `<tr><td colspan="10" class="empty">该时间范围暂无请求。运行 claude-obs / cfuse-obs 后会自动出现。</td></tr>`;
    return;
  }
  tbody.innerHTML = STATE.traces.map((t,i) => {
    const ok = t.status && t.status>=200 && t.status<300;
    const cls = ok ? "status-ok" : "status-err";
    const flash = newIds && newIds.has(t.trace_id) ? " flash" : "";
    const sel = STATE.selected===t.trace_id ? " selected" : "";
    return `<tr class="row-link${flash}${sel}" data-id="${esc(t.trace_id)}" data-ts="${t.ts_start}">
      <td>${esc(fmtTs(t.ts_start))}</td>
      <td><span class="badge">${esc(t.client_hint||"—")}</span></td>
      <td>${esc(t.upstream)}</td>
      <td>${esc(t.model||"—")}</td>
      <td class="${cls}">${esc(t.status ?? "—")}${t.error?" ⚠":""}</td>
      <td class="number">${esc(fmtMs(t.ttft_ms))}</td>
      <td class="number">${esc(fmtMs(t.total_ms))}</td>
      <td class="number">${esc(fmtNum(t.tokens_in))}/${esc(fmtNum(t.tokens_out))}</td>
      <td class="number">${esc(t.tool_call_count||0)}</td>
      <td><code>${esc(t.path)}</code></td>
    </tr>`;
  }).join("");
  tbody.querySelectorAll("tr.row-link").forEach(tr => {
    tr.addEventListener("click", () => showTrace(tr.dataset.id, tr.dataset.ts));
  });
}

// ---- 点击行：懒加载详情 ----
async function showTrace(id, ts){
  STATE.selected = id;
  document.querySelectorAll("#traces-table tr.row-link").forEach(tr =>
    tr.classList.toggle("selected", tr.dataset.id===id));
  const root = document.getElementById("trace-detail");
  root.innerHTML = `<div class="detail"><div class="small">加载中…</div></div>`;
  try{
    const r = await fetch(`/api/trace/${encodeURIComponent(id)}?ts=${encodeURIComponent(ts||"")}`, {cache:"no-store"});
    const d = await r.json();
    if(d.error){ root.innerHTML = `<div class="detail"><div class="empty">${esc(d.error)}</div></div>`; return; }
    root.innerHTML = renderDetail(id, d);
  }catch(e){
    root.innerHTML = `<div class="detail"><div class="empty">加载失败：${esc(e)}</div></div>`;
  }
}

function renderContext(ctx){
  if(!ctx || !ctx.available){
    return `<h4>上下文</h4><div class="small">无结构化上下文（请求体非 JSON 或格式不支持）</div>`;
  }
  const tb = ctx.token_breakdown||{};
  const bar = `
    <div class="ctxbar" title="估算 token 占比">
      <span class="seg seg-sys" style="width:${tb.system_pct||0}%"></span>
      <span class="seg seg-tool" style="width:${tb.tools_pct||0}%"></span>
      <span class="seg seg-msg" style="width:${tb.messages_pct||0}%"></span>
    </div>
    <div class="small">
      约 ${tb.total_estimated||0} token ·
      <span class="dot dot-sys"></span> 系统提示 ${tb.system||0} (${tb.system_pct||0}%) ·
      <span class="dot dot-tool"></span> 工具菜单 ${tb.tools||0} (${tb.tools_pct||0}%) ·
      <span class="dot dot-msg"></span> 历史消息 ${tb.messages||0} (${tb.messages_pct||0}%)
    </div>`;
  const tools = (ctx.tools||[]).map(t =>
    `<details><summary>
        <span class="badge badge-${esc(t.origin.split('(')[0])}">${esc(t.origin)}</span>
        <b>${esc(t.name)}</b>
        <span class="small">· 描述约 ${t.description_tokens}t · Schema 约 ${t.schema_tokens}t</span>
      </summary>
      <div class="small" style="margin:4px 0">${esc(t.description)}</div>
      <pre>${esc(t.schema)}</pre>
    </details>`).join("") || `<div class="small">无</div>`;
  const msgs = (ctx.messages||[]).map(m => {
    const flags=[]; if(m.has_tool_use)flags.push("tool_use"); if(m.has_tool_result)flags.push("tool_result");
    const f = flags.length?` <span class="badge">${flags.join(",")}</span>`:"";
    return `<details><summary>
        <span class="badge badge-role-${esc(m.role)}">${esc(m.role)}</span>
        <span class="small">#${m.index} · 约 ${m.tokens}t · ${m.chars} 字符</span>${f}
      </summary><pre>${esc(m.preview)}</pre></details>`;
  }).join("") || `<div class="small">无</div>`;
  const sysText = (ctx.system&&ctx.system.text)||"";
  const sysBlock = sysText
    ? `<details><summary><span class="small">约 ${ctx.system.tokens}t · ${ctx.system.chars} 字符</span></summary><pre>${esc(sysText)}</pre></details>`
    : `<div class="small">无</div>`;
  return `
    <h4>上下文 — 模型实际看到的全部内容</h4>
    ${bar}
    <h4>系统提示（System prompt）</h4>
    ${sysBlock}
    <h4>工具菜单（${ctx.tools_count||0}）— skill / MCP 暴露给模型的"菜单"</h4>
    ${tools}
    <h4>历史消息（${ctx.messages_count||0}）— 上下文分层</h4>
    ${msgs}`;
}

function renderDetail(id, d){
  const s = d.summary||{};
  const chunks = (d.chunks||[]).map(c =>
    `<span class="chunk ${esc(c.kind)}" title="seq=${c.seq} @ ${c.ts_offset_ms.toFixed(0)}ms">${esc(c.kind==="pause"?"⏸"+c.text:(c.text||c.kind))}</span>`
  ).join("");
  const tools = (d.tool_calls||[]).map(tc =>
    `<details><summary>${esc(tc.name)} (${esc(tc.tool_id)}) ${tc.parsed_ok?"":"⚠ 未能解析"}</summary><pre>${esc(tc.arguments_json)}</pre></details>`
  ).join("") || `<div class="small">无</div>`;
  const pauses = (d.pauses_ms||[]).length
    ? d.pauses_ms.map(p => `<span class="badge">${p.toFixed(0)}ms</span>`).join(" ")
    : `<span class="small">无</span>`;
  return `<div class="detail">
      <h4>请求 ${esc(id)}</h4>
      <div class="small">${esc(s.client_hint)} → ${esc(s.upstream)} · ${esc(s.path)}</div>
      ${renderContext(d.context)}
      <h4>停顿点（&gt;800ms）</h4>
      <div>${pauses}</div>
      <h4>切词时间线（${(d.chunks||[]).length} 个事件）</h4>
      <div class="chunks">${chunks || `<span class="small">无 chunks</span>`}</div>
      <h4>工具调用</h4>
      ${tools}
      <h4>请求体（原文）</h4>
      <pre>${esc(JSON.stringify(d.request_body ?? d.request_body_ref ?? "", null, 2))}</pre>
      <h4>请求头（已脱敏）</h4>
      <pre>${esc(JSON.stringify(d.request_headers||{}, null, 2))}</pre>
      <h4>响应文本</h4>
      <pre>${esc(d.response_text||"")}</pre>
    </div>`;
}

function renderTools(){
  const root = document.getElementById("tools-root");
  const tools = STATE.tools||{};
  const names = Object.keys(tools);
  if(!names.length){
    root.innerHTML = `<div class="card empty">该时间范围暂无工具调用。</div>`;
    return;
  }
  root.innerHTML = `<div class="card"><h3>工具调用统计（流式响应中提取）</h3><table>
    <thead><tr><th>工具</th><th class="number">调用次数</th><th class="number">解析成功</th><th class="number">解析失败</th><th>参数示例</th></tr></thead>
    <tbody>${names.map(n => {
      const s = tools[n];
      const sample = (s.sample_arguments||[]).map(a => `<details><summary>参数</summary><pre>${esc(a)}</pre></details>`).join("");
      return `<tr><td>${esc(n)}</td><td class="number">${s.count}</td>
        <td class="number status-ok">${s.parsed_ok}</td>
        <td class="number status-err">${s.parsed_fail}</td><td>${sample}</td></tr>`;
    }).join("")}</tbody></table></div>`;
}

function renderMcp(){
  const root = document.getElementById("mcp-root");
  const sessions = STATE.mcp||[];
  if(!sessions.length){
    root.innerHTML = `<div class="card empty">暂无 stdio MCP 会话。用 <code>obs mcp -- &lt;你的 mcp 命令&gt;</code> 包一层即可抓取。</div>`;
    return;
  }
  root.innerHTML = `<div class="card"><h3>stdio MCP 会话（JSON-RPC 抓取）</h3>` +
    sessions.map(sess => {
      const frames = (sess.frames||[]).map(fr =>
        `<details><summary><span class="badge">${esc(fr.direction||"")}</span> ${esc(fr.method||fr.kind||"")} <span class="small">@${esc(fmtTs(fr.ts))}</span></summary><pre>${esc(JSON.stringify(fr.payload, null, 2))}</pre></details>`
      ).join("");
      return `<div class="card" style="margin-top:8px">
        <h3>会话 ${esc(sess.session_id||"")} · ${esc(sess.command||"")}</h3>
        <div class="small">${(sess.frames||[]).length} 帧</div>${frames}</div>`;
    }).join("") + `</div>`;
}

// ---- tab 切换 ----
document.querySelectorAll("nav button").forEach(b => {
  b.addEventListener("click", () => {
    document.querySelectorAll("nav button").forEach(x => x.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(x => x.classList.remove("active"));
    b.classList.add("active");
    document.getElementById("tab-"+b.dataset.tab).classList.add("active");
  });
});
document.getElementById("date-sel").addEventListener("change", poll);

// ---- 轮询循环 ----
let timer = null;
function startPolling(){ if(timer) clearInterval(timer); timer = setInterval(() => {
  if(document.getElementById("autorefresh").checked) poll();
}, 3000); }
poll();
startPolling();
</script>
</body>
</html>"""


if __name__ == "__main__":
    raise SystemExit(main())
