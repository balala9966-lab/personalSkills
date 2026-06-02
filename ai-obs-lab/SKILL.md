---
name: ai-obs-lab
description: |
  Local AI observability lab. Run a stdlib-only HTTP reverse proxy that captures
  every request/response between AI coding tools (Claude Code, Codex, CodeFuse,
  Cursor) and their LLM upstreams — including streaming SSE chunk timing, tool
  calls, MCP JSON-RPC payloads, and full prompts. Also runs A/B eval suites with
  objective metrics and optional LLM-as-Judge. Outputs JSONL logs + a
  single-file HTML dashboard.

  Trigger this skill when the user wants to:
    * observe what a model is actually seeing / generating
    * inspect tool_calls / function-calling JSON
    * trace LLM requests / capture prompts
    * A/B test prompt versions, measure variance / schema compliance / token cost
    * understand TTFT / token-per-second / pause points
    * debug "why did the model do X" with full request/response fidelity

  Trigger phrases (zh): 观测模型, prompt 评测, 看 tool_calls, AI 可观测性,
    trace LLM, prompt A/B, 流式节奏, 上下文审计, 黑盒, ai-obs-lab,
    可观测性实验台, 抓 LLM 请求, 无感观测, claude-obs, cfuse-obs,
    理解 skill 原理, 理解 mcp 原理, 看模型上下文, 看切词, 看 skill 工作过程
  Trigger phrases (en): observe model, prompt eval, trace LLM, tool calls,
    AB test prompt, observability, capture proxy, ai-obs-lab,
    claude-obs, cfuse-obs, understand skill, understand mcp, context audit
---

# ai-obs-lab — AI Observability Lab (skill)

## What this is

A local-only toolkit that turns the black-box interaction between AI coding
tools and their LLM backends into structured, comparable, replayable data.

Three pillars:

1. **Capture Proxy** — stdlib HTTP reverse proxy on `127.0.0.1:8788`. Routes
   `/anthropic/*` `/openai/*` `/upstream/<profile>/*` to real upstreams while
   recording every prompt, tool schema, SSE chunk timestamp, tool call and
   response token to JSONL.
2. **A/B Eval Runner** — YAML suite of `(version, case)` × N repeats, computes
   output-variance, JSON-schema compliance, keyword hit rate, logprobs top-1,
   TTFT / token stats. Optional LLM-as-Judge (4-axis rubric).
3. **Live Dashboard + Static HTML Report** — 两种看板：
   - **实时看板**（`obs live`，stdlib `http.server` on `127.0.0.1:8799`）：浏览器
     每 3 秒轮询，**新 trace 自动插顶 + 闪烁高亮**，点行懒加载详情，边跑边看。
   - **静态报告**（`obs report`）：单文件自包含 HTML，可离线 `open`，适合存档分享。
   两者三个 tab：请求追踪、评测对比、工具与 MCP。每条 trace 详情含 **上下文面板**
   （system / tools 菜单含 MCP/builtin/skill 来源标注 / messages 分层 + token 占比）
   + 切词时间线 + pause 高亮。这是理解 skill / MCP 工作原理的核心视图：看清模型
   实际"看到"了什么、token 被什么吃掉。**界面为中文，但 trace 原文 / JSON / 参数名
   / 模型名 / 状态码保持原样不翻译。**
4. **stdio MCP Wrapper** — `obs mcp -- <真实 mcp server 命令>` 把任意 stdio MCP
   server 包在中间，双向透明转发 stdin/stdout 的同时把每帧 JSON-RPC
   （`initialize` / `tools/list` / `tools/call` / `result` …）tee 到
   `logs/<date>/mcp/<session>.jsonl`，由实时看板「工具与 MCP」tab 展示。这样
   stdio MCP 的工具菜单与每次调用的 params/result 也可观测。

## How to invoke

### 无感观测（推荐）—— 零负担包装命令

```bash
# 一次性安装：
echo 'source <repo>/ai-obs-lab/bin/obs.sh' >> ~/.zshrc && source ~/.zshrc

# 照常用，命令加 -obs 后缀；原 claude / cfuse 不受影响：
claude-obs              # 交互式 Claude Code，全程被观测
cfuse-obs               # 交互式 CodeFuse，全程被观测
obs live               # 启动实时观测看板（浏览器自动刷新，推荐）
obs mcp -- <命令>      # 包一层 stdio MCP server，抓取 JSON-RPC
obs report             # 生成静态 HTML 快照报告（含「上下文面板」）
obs tail / obs status / obs stop
```

包装层自动拉起代理、把 BASE_URL 指向代理（claude 用临时 settings、cfuse 用 env）、
透传全部参数。token 由工具自带、代理原样转发。

### 手动接入

```bash
# Start proxy + live tail (default):
bash ai-obs-lab/start.sh

# Point a client at the proxy (Claude Code example):
export ANTHROPIC_BASE_URL=http://127.0.0.1:8788/anthropic

# Run an A/B eval:
python -m ai_obs_lab.cli eval \
  --suite ai-obs-lab/src/ai_obs_lab/eval/suites/json-extract.example.yaml \
  --repeat 10 [--judge]

# Generate today's HTML report and open it:
bash ai-obs-lab/start.sh report
```

`PYTHONPATH=ai-obs-lab/src` is required if you don't run `pip install -e .`.

## Key files

- `src/ai_obs_lab/cli.py` — unified entry: `proxy | eval | report | tail | serve | mcp`
- `src/ai_obs_lab/proxy/server.py` — capture proxy（HTTP 反向代理）
- `src/ai_obs_lab/proxy/sse_parser.py` — Anthropic + OpenAI SSE parser
- `src/ai_obs_lab/proxy/mcp_stdio.py` — stdio MCP wrapper（双向转发 + tee JSON-RPC 帧）
- `src/ai_obs_lab/eval/runner.py` — eval engine
- `src/ai_obs_lab/eval/judge.py` — LLM-as-Judge
- `src/ai_obs_lab/dashboard/server.py` — 实时看板 HTTP 服务（`obs live`）
- `src/ai_obs_lab/dashboard/html.py` — static report generator（中文界面）
- `src/ai_obs_lab/dashboard/tail.py` — 终端实时流水（中文表头）
- `src/ai_obs_lab/dashboard/query.py` — `parse_request_context` 拆 system/tools/messages
- `src/ai_obs_lab/core/store.py` — JSONL 存储，含 `append_mcp_frame` / `iter_mcp_sessions`
- `bin/obs.sh` — 无感观测包装层（claude-obs / cfuse-obs / obs live / obs mcp）
- `config/proxy.example.yaml` — proxy config template

## Important constraints

- Stdlib-only in Phase 1 (no fastapi / requests / pydantic).
- API keys are **never** persisted; only `sha256:<hex8>` fingerprint.
- Logs live in `~/.ai-obs-lab/logs/YYYY-MM-DD/` — local only, not transmitted.
- Phase 2 path: `scripts/extract_to_standalone.sh` moves the tree to
  `~/IdeaProjects/ai-obs-lab/` and enables `pip install -e .` + `aolab` CLI.

See `README.md` for client setup (Claude Code / Codex / CodeFuse).
