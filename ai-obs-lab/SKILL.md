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
3. **Static HTML Dashboard** — one self-contained file you can `open` offline.
   Three tabs: trace timeline, eval comparison, tool-call / MCP panel. 每条
   trace 详情含 **Context 面板**（system / tools 菜单含 MCP/builtin/skill 来源
   标注 / messages 分层 + token 占比）+ chunk timeline + pause 高亮。这是理解
   skill / MCP 工作原理的核心视图：看清模型实际"看到"了什么、token 被什么吃掉。

## How to invoke

### 无感观测（推荐）—— 零负担包装命令

```bash
# 一次性安装：
echo 'source <repo>/ai-obs-lab/bin/obs.sh' >> ~/.zshrc && source ~/.zshrc

# 照常用，命令加 -obs 后缀；原 claude / cfuse 不受影响：
claude-obs              # 交互式 Claude Code，全程被观测
cfuse-obs               # 交互式 CodeFuse，全程被观测
obs report             # 打开含「上下文面板」的 HTML 报告
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

- `src/ai_obs_lab/cli.py` — unified entry: `proxy | eval | report | tail`
- `src/ai_obs_lab/proxy/server.py` — capture proxy
- `src/ai_obs_lab/proxy/sse_parser.py` — Anthropic + OpenAI SSE parser
- `src/ai_obs_lab/eval/runner.py` — eval engine
- `src/ai_obs_lab/eval/judge.py` — LLM-as-Judge
- `src/ai_obs_lab/dashboard/html.py` — static report generator
- `src/ai_obs_lab/dashboard/query.py` — `parse_request_context` 拆 system/tools/messages
- `bin/obs.sh` — 无感观测包装层（claude-obs / cfuse-obs / obs）
- `config/proxy.example.yaml` — proxy config template

## Important constraints

- Stdlib-only in Phase 1 (no fastapi / requests / pydantic).
- API keys are **never** persisted; only `sha256:<hex8>` fingerprint.
- Logs live in `~/.ai-obs-lab/logs/YYYY-MM-DD/` — local only, not transmitted.
- Phase 2 path: `scripts/extract_to_standalone.sh` moves the tree to
  `~/IdeaProjects/ai-obs-lab/` and enables `pip install -e .` + `aolab` CLI.

See `README.md` for client setup (Claude Code / Codex / CodeFuse).
