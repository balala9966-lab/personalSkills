"""Static HTML report generator.

Reads `query.dashboard_snapshot` and produces a single self-contained HTML
file. No frameworks — embedded vanilla JS renders the tabs and trace detail
panel. Designed to be opened directly with `file://` or `open report.html`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

from ..core.store import JSONLStore
from . import query as Q


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>AI 观测实验台 · 报告</title>
<style>
  :root {
    --bg: #0f1115; --fg: #e6e6e6; --muted: #9aa3af; --card: #161a22;
    --accent: #6ea8fe; --warn: #f4b860; --err: #ef6a6a; --ok: #79d18a;
    --border: #2a313c;
  }
  html, body { background: var(--bg); color: var(--fg);
    font: 13px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", monospace; margin: 0; }
  header { padding: 14px 20px; border-bottom: 1px solid var(--border); display: flex; gap: 16px; align-items: baseline; }
  header h1 { margin: 0; font-size: 16px; }
  header .meta { color: var(--muted); font-size: 12px; }
  nav { display: flex; gap: 8px; padding: 8px 20px; border-bottom: 1px solid var(--border); }
  nav button { background: var(--card); color: var(--fg); border: 1px solid var(--border);
    padding: 6px 12px; border-radius: 4px; cursor: pointer; font: inherit; }
  nav button.active { border-color: var(--accent); color: var(--accent); }
  main { padding: 16px 20px; }
  .grid { display: grid; gap: 12px; }
  .grid.kpi { grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 12px; }
  .card h3 { margin: 0 0 6px; font-size: 12px; color: var(--muted); font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
  .card .v { font-size: 20px; font-weight: 600; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th, td { padding: 6px 10px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }
  th { color: var(--muted); font-weight: 500; background: rgba(255,255,255,0.02); position: sticky; top: 0; }
  tr.row-link { cursor: pointer; }
  tr.row-link:hover { background: rgba(110,168,254,0.08); }
  .status-ok { color: var(--ok); }
  .status-err { color: var(--err); }
  .badge { display: inline-block; padding: 1px 6px; border-radius: 3px; background: rgba(255,255,255,0.06); font-size: 11px; }
  .panel { display: none; }
  .panel.active { display: block; }
  .detail { background: var(--card); border: 1px solid var(--border); border-radius: 6px;
    padding: 12px; margin-top: 12px; max-height: 70vh; overflow: auto; }
  .detail h4 { margin: 12px 0 4px; color: var(--accent); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
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
  .diff-row td { font-family: ui-monospace, SFMono-Regular, monospace; font-size: 12px; }
  .number { text-align: right; font-variant-numeric: tabular-nums; }
  /* Context token breakdown bar */
  .ctxbar { display: flex; height: 14px; border-radius: 4px; overflow: hidden; margin: 4px 0; border: 1px solid var(--border); }
  .ctxbar .seg { height: 100%; }
  .seg-sys { background: #c084fc; }
  .seg-tool { background: var(--accent); }
  .seg-msg { background: var(--ok); }
  .dot { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 2px; }
  .dot-sys { background: #c084fc; }
  .dot-tool { background: var(--accent); }
  .dot-msg { background: var(--ok); }
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
  <span class="meta">生成于 <span id="gen-at"></span> · 范围 <span id="range"></span></span>
</header>
<nav>
  <button data-tab="traces" class="active">请求追踪</button>
  <button data-tab="evals">评测对比</button>
  <button data-tab="tools">工具与 MCP</button>
</nav>
<main>
  <section id="tab-traces" class="panel active">
    <div class="grid kpi" id="kpis"></div>
    <div class="card" style="margin-top:12px">
      <h3>最近请求（点击行查看完整上下文）</h3>
      <div style="max-height: 60vh; overflow: auto">
        <table id="traces-table">
          <thead>
            <tr>
              <th>时间</th><th>客户端</th><th>上游</th><th>模型</th>
              <th>状态</th><th class="number">首字延迟</th><th class="number">总耗时</th>
              <th class="number">token 入/出</th><th class="number">工具数</th><th>路径</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <div id="trace-detail"></div>
    </div>
  </section>
  <section id="tab-evals" class="panel">
    <div id="evals-root"></div>
  </section>
  <section id="tab-tools" class="panel">
    <div id="tools-root"></div>
  </section>
</main>

<script id="DATA" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById("DATA").textContent);

function fmtTs(ts) {
  if (!ts) return "";
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString();
}
function fmtMs(v) { return v == null ? "—" : (v < 1000 ? v.toFixed(0)+"ms" : (v/1000).toFixed(2)+"s"); }
function fmtNum(v) { return v == null ? "—" : String(v); }
function esc(s) {
  if (s == null) return "";
  return String(s).replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
}

function renderKPIs() {
  const o = DATA.overview || {};
  const cards = [
    ["总请求数", o.total ?? 0],
    ["错误数", o.errors ?? 0],
    ["平均首字延迟", fmtMs(o.avg_ttft_ms)],
    ["token 输入", o.tokens_in_total ?? 0],
    ["token 输出", o.tokens_out_total ?? 0],
    ["工具调用次数", o.tool_call_total ?? 0],
  ];
  document.getElementById("kpis").innerHTML = cards.map(
    ([k, v]) => `<div class="card"><h3>${esc(k)}</h3><div class="v">${esc(v)}</div></div>`
  ).join("");
}

function renderTraces() {
  const tbody = document.querySelector("#traces-table tbody");
  if (!DATA.traces || !DATA.traces.length) {
    tbody.innerHTML = `<tr><td colspan="10" class="empty">该时间范围暂无请求。</td></tr>`;
    return;
  }
  tbody.innerHTML = DATA.traces.map((t, i) => {
    const statusCls = t.status && t.status >= 200 && t.status < 300 ? "status-ok" : "status-err";
    return `<tr class="row-link" data-i="${i}">
      <td>${esc(fmtTs(t.ts_start))}</td>
      <td><span class="badge">${esc(t.client_hint || "—")}</span></td>
      <td>${esc(t.upstream)}</td>
      <td>${esc(t.model || "—")}</td>
      <td class="${statusCls}">${esc(t.status ?? "—")}${t.error ? " ⚠" : ""}</td>
      <td class="number">${esc(fmtMs(t.ttft_ms))}</td>
      <td class="number">${esc(fmtMs(t.total_ms))}</td>
      <td class="number">${esc(fmtNum(t.tokens_in))}/${esc(fmtNum(t.tokens_out))}</td>
      <td class="number">${esc(t.tool_call_count || 0)}</td>
      <td><code>${esc(t.path)}</code></td>
    </tr>`;
  }).join("");
  tbody.querySelectorAll("tr.row-link").forEach(tr => {
    tr.addEventListener("click", () => showTrace(parseInt(tr.dataset.i)));
  });
}

function renderContext(ctx) {
  if (!ctx || !ctx.available) {
    return `<h4>上下文</h4><div class="small">无结构化上下文（请求体非 JSON 或格式不支持）</div>`;
  }
  const tb = ctx.token_breakdown || {};
  // token 占比条：system / tools / messages，让你直观看到上下文被什么填满
  const bar = `
    <div class="ctxbar" title="估算 token 占比">
      <span class="seg seg-sys" style="width:${tb.system_pct || 0}%"></span>
      <span class="seg seg-tool" style="width:${tb.tools_pct || 0}%"></span>
      <span class="seg seg-msg" style="width:${tb.messages_pct || 0}%"></span>
    </div>
    <div class="small">
      约 ${tb.total_estimated || 0} token ·
      <span class="dot dot-sys"></span> 系统提示 ${tb.system || 0} (${tb.system_pct || 0}%) ·
      <span class="dot dot-tool"></span> 工具菜单 ${tb.tools || 0} (${tb.tools_pct || 0}%) ·
      <span class="dot dot-msg"></span> 历史消息 ${tb.messages || 0} (${tb.messages_pct || 0}%)
    </div>`;

  // tools 菜单：这就是 skill / MCP 暴露给模型的"菜单"
  const tools = (ctx.tools || []).map(t =>
    `<details><summary>
        <span class="badge badge-${esc(t.origin.split('(')[0])}">${esc(t.origin)}</span>
        <b>${esc(t.name)}</b>
        <span class="small">· 描述约 ${t.description_tokens}t · Schema 约 ${t.schema_tokens}t</span>
      </summary>
      <div class="small" style="margin:4px 0">${esc(t.description)}</div>
      <pre>${esc(t.schema)}</pre>
    </details>`
  ).join("") || `<div class="small">无</div>`;

  // messages 分层：token 主要被这部分吃掉
  const msgs = (ctx.messages || []).map(m => {
    const flags = [];
    if (m.has_tool_use) flags.push("tool_use");
    if (m.has_tool_result) flags.push("tool_result");
    const flagStr = flags.length ? ` <span class="badge">${flags.join(",")}</span>` : "";
    return `<details><summary>
        <span class="badge badge-role-${esc(m.role)}">${esc(m.role)}</span>
        <span class="small">#${m.index} · 约 ${m.tokens}t · ${m.chars} 字符</span>${flagStr}
      </summary>
      <pre>${esc(m.preview)}</pre>
    </details>`;
  }).join("") || `<div class="small">无</div>`;

  const sysText = (ctx.system && ctx.system.text) || "";
  const sysBlock = sysText
    ? `<details><summary><span class="small">约 ${ctx.system.tokens}t · ${ctx.system.chars} 字符</span></summary><pre>${esc(sysText)}</pre></details>`
    : `<div class="small">无</div>`;

  return `
    <h4>上下文 — 模型实际看到的全部内容</h4>
    ${bar}
    <h4>系统提示（System prompt）</h4>
    ${sysBlock}
    <h4>工具菜单（${ctx.tools_count || 0}）— skill / MCP 暴露给模型的"菜单"</h4>
    ${tools}
    <h4>历史消息（${ctx.messages_count || 0}）— 上下文分层</h4>
    ${msgs}`;
}

function showTrace(i) {
  const t = DATA.traces[i];
  const detail = DATA.trace_details ? DATA.trace_details[t.trace_id] : null;
  const root = document.getElementById("trace-detail");
  if (!detail) {
    root.innerHTML = `<div class="detail"><div class="empty">未内联 trace 详情（请用 --inline-details 重新生成）</div></div>`;
    return;
  }
  const chunks = (detail.chunks || []).map(c =>
    `<span class="chunk ${esc(c.kind)}" title="seq=${c.seq} @ ${c.ts_offset_ms.toFixed(0)}ms">${esc(c.kind === "pause" ? "⏸" + c.text : (c.text || c.kind))}</span>`
  ).join("");
  const tools = (detail.tool_calls || []).map(tc =>
    `<details><summary>${esc(tc.name)} (${esc(tc.tool_id)}) ${tc.parsed_ok ? "" : "⚠ 未能解析"}</summary><pre>${esc(tc.arguments_json)}</pre></details>`
  ).join("") || `<div class="small">无</div>`;
  const pauses = (detail.pauses_ms || []).length
    ? detail.pauses_ms.map(p => `<span class="badge">${p.toFixed(0)}ms</span>`).join(" ")
    : `<span class="small">无</span>`;
  root.innerHTML = `
    <div class="detail">
      <h4>请求 ${esc(t.trace_id)}</h4>
      <div class="small">${esc(t.client_hint)} → ${esc(t.upstream)} · ${esc(t.path)}</div>
      ${renderContext(detail.context)}
      <h4>停顿点（&gt;800ms）</h4>
      <div>${pauses}</div>
      <h4>切词时间线（${(detail.chunks || []).length} 个事件）</h4>
      <div class="chunks">${chunks || `<span class="small">无 chunks</span>`}</div>
      <h4>工具调用</h4>
      ${tools}
      <h4>请求体（原文）</h4>
      <pre>${esc(JSON.stringify(detail.request_body ?? detail.request_body_ref ?? "", null, 2))}</pre>
      <h4>请求头（已脱敏）</h4>
      <pre>${esc(JSON.stringify(detail.request_headers || {}, null, 2))}</pre>
      <h4>响应文本</h4>
      <pre>${esc(detail.response_text || "")}</pre>
    </div>`;
}

function renderEvals() {
  const root = document.getElementById("evals-root");
  if (!DATA.eval_runs || !DATA.eval_runs.length) {
    root.innerHTML = `<div class="card empty">该时间范围暂无评测记录。</div>`;
    return;
  }
  root.innerHTML = DATA.eval_runs.map(er => {
    const m = er.meta;
    const cmp = er.compare;
    const judge = er.judge || {};
    const cases = Object.keys(cmp.table);
    const tables = cases.map(caseId => {
      const versions = Object.keys(cmp.table[caseId]);
      const head = `<tr><th>指标</th>${versions.map(v => `<th>${esc(v)}</th>`).join("")}</tr>`;
      const metrics = [
        ["similarity_variance", "相似度方差"],
        ["schema_compliance_rate", "Schema 合规率"],
        ["keyword_hit_rate", "关键词命中率"],
        ["avg_logprob_top1", "top1 对数概率"],
        ["avg_ttft_ms", "首字延迟(ms)"],
        ["avg_tokens_out", "输出 token"],
        ["errors", "错误数"],
      ];
      const rows = metrics.map(([k, label]) => {
        const cells = versions.map(v => {
          const val = cmp.table[caseId][v][k];
          return `<td class="number">${esc(val == null ? "—" : (typeof val === "number" ? val.toFixed(3) : val))}</td>`;
        }).join("");
        return `<tr><td>${esc(label)}</td>${cells}</tr>`;
      }).join("");
      // Judge scores if present
      const j = judge[caseId] || {};
      const judgeRows = ["overall","correctness","format","conciseness","faithfulness"].map(axis => {
        const cells = versions.map(v => {
          const val = (j[v] || {})[axis];
          return `<td class="number">${val == null ? "—" : val.toFixed(2)}</td>`;
        }).join("");
        return `<tr><td>judge:${esc(axis)}</td>${cells}</tr>`;
      }).join("");
      const samples = versions.map(v => {
        const out = (cmp.table[caseId][v].sample_outputs || [])[0] || "";
        return `<details><summary>${esc(v)} 输出示例</summary><pre>${esc(out)}</pre></details>`;
      }).join("");
      return `<div class="card" style="margin-top:8px">
        <h3>用例 ${esc(caseId)}</h3>
        <table>${head}${rows}${judgeRows}</table>
        ${samples}
      </div>`;
    }).join("");
    return `<div class="card" style="margin-bottom:16px">
      <h3>${esc(m.suite_name)} · ${esc(m.model)} · T=${esc(m.temperature)} · repeat=${esc(m.repeat)}</h3>
      <div class="small">${esc(m.eval_run_id)} · ${esc(fmtTs(m.ts_start))}</div>
      ${tables}
    </div>`;
  }).join("");
}

function renderTools() {
  const root = document.getElementById("tools-root");
  const tools = DATA.tools || {};
  const names = Object.keys(tools);
  if (!names.length) {
    root.innerHTML = `<div class="card empty">该时间范围暂无工具调用。</div>`;
    return;
  }
  root.innerHTML = `<div class="card"><h3>工具调用统计（流式响应中提取）</h3><table>
    <thead><tr><th>工具</th><th class="number">调用次数</th><th class="number">解析成功</th><th class="number">解析失败</th><th>参数示例</th></tr></thead>
    <tbody>${names.map(n => {
      const s = tools[n];
      const sample = (s.sample_arguments || [])
        .map(a => `<details><summary>参数</summary><pre>${esc(a)}</pre></details>`).join("");
      return `<tr><td>${esc(n)}</td>
        <td class="number">${s.count}</td>
        <td class="number status-ok">${s.parsed_ok}</td>
        <td class="number status-err">${s.parsed_fail}</td>
        <td>${sample}</td></tr>`;
    }).join("")}</tbody></table></div>`;
}

// Tab switching.
document.querySelectorAll("nav button").forEach(b => {
  b.addEventListener("click", () => {
    document.querySelectorAll("nav button").forEach(x => x.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(x => x.classList.remove("active"));
    b.classList.add("active");
    document.getElementById("tab-" + b.dataset.tab).classList.add("active");
  });
});

document.getElementById("gen-at").textContent = DATA.generated_at || "";
document.getElementById("range").textContent =
  (DATA.range?.start || "auto") + " → " + (DATA.range?.end || "auto");
renderKPIs();
renderTraces();
renderEvals();
renderTools();
</script>
</body>
</html>
"""


def _resolve_range(spec: str | None) -> tuple[date | None, date | None]:
    """Parse '--date today | yesterday | YYYY-MM-DD | YYYY-MM-DD:YYYY-MM-DD | all'."""
    if not spec or spec == "all":
        return None, None
    if spec == "today":
        d = date.today()
        return d, d
    if spec == "yesterday":
        d = date.today() - timedelta(days=1)
        return d, d
    if ":" in spec:
        a, b = spec.split(":", 1)
        return _parse_date(a), _parse_date(b)
    d = _parse_date(spec)
    return d, d


def _parse_date(s: str) -> date:
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


def build_html(
    store: JSONLStore,
    *,
    date_spec: str | None = "today",
    inline_details: bool = True,
    trace_limit: int = 200,
) -> str:
    start, end = _resolve_range(date_spec)
    snap = Q.dashboard_snapshot(store, start=start, end=end, trace_limit=trace_limit)
    if inline_details:
        details: dict[str, dict] = {}
        for t in snap["traces"]:
            try:
                tf = store.load_trace(t["trace_id"], ts=t["ts_start"])
                d = tf.to_dict()
                # 注入"完整上下文"结构化视图：system / tools 菜单 / messages 分层。
                # 这是理解 skill / MCP 工作原理的核心，让你看清模型实际"看到"了什么。
                d["context"] = Q.parse_request_context(d.get("request_body"))
                details[t["trace_id"]] = d
            except FileNotFoundError:
                continue
        snap["trace_details"] = details
    data_json = json.dumps(snap, ensure_ascii=False, default=str)
    # Defend against `</script>` sequences appearing inside data.
    data_json = data_json.replace("</", "<\\/")
    return _HTML_TEMPLATE.replace("__DATA__", data_json)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ai_obs_lab.dashboard.html")
    p.add_argument("--date", default="today",
                   help="today | yesterday | YYYY-MM-DD | YYYY-MM-DD:YYYY-MM-DD | all")
    p.add_argument("--out", default="~/.ai-obs-lab/report.html")
    p.add_argument("--log-dir", default=None)
    p.add_argument("--limit", type=int, default=200)
    p.add_argument("--no-inline-details", action="store_true",
                   help="Skip embedding per-trace full bodies (smaller HTML)")
    p.add_argument("--open", action="store_true", help="Open the report in default browser")
    args = p.parse_args(argv)

    store = JSONLStore(args.log_dir) if args.log_dir else JSONLStore()
    html = build_html(
        store,
        date_spec=args.date,
        inline_details=not args.no_inline_details,
        trace_limit=args.limit,
    )
    out_path = Path(os.path.expanduser(args.out)).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    sys.stderr.write(f"[ai-obs-lab] wrote report: {out_path}\n")
    if args.open:
        webbrowser.open(f"file://{out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
