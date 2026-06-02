# ai-obs-lab

Local AI observability lab. Capture every LLM request your AI coding tools
make, A/B-test prompts, and view it all in a single offline HTML dashboard.

> **Phase 1 (this repo, current):** stdlib-only Python toolkit, lives inside
> `personalSkills/`. **Phase 2 (future):** `scripts/extract_to_standalone.sh`
> moves it to its own repo at `~/IdeaProjects/ai-obs-lab/` with FastAPI Web UI
> + `pip install -e .` + `aolab` CLI.

## Why

You've probably had this experience: Claude Code does something weird, or your
prompt produces wildly different output on consecutive runs. The chat UI hides
*everything that matters*: the full system prompt, the tool schemas injected,
the streaming token timing, the exact JSON the model produced for `tool_calls`.

`ai-obs-lab` is what you reach for when you stop treating LLMs as oracles and
start debugging them like microservices.

## What it captures

| Layer | What you see |
|-------|--------------|
| **HTTP** | full request body (`system`, `messages`, `tools`), redacted headers (`Authorization` → `sha256:<hex8>`), status, total latency |
| **Context** | system prompt / tools 菜单（自动标注 MCP / builtin / skill 来源）/ messages 分层 + token 占比，看清模型实际"看到"了什么 |
| **Streaming** | per-chunk timestamps → TTFT, tokens/s, **pause points >800ms** highlighted in the dashboard |
| **Tool calls** | extracted `tool_use` / `tool_calls` per stream (parsed JSON or raw if malformed), aggregated by tool name |
| **Tokens** | `input_tokens` / `output_tokens` from both Anthropic streaming `message_delta` and OpenAI non-stream `usage` |
| **Errors** | upstream HTTP errors are still recorded (status + body) so you can see *why* a tool failed |
| **Eval runs** | `(version, case) × N` with similarity variance, JSON schema compliance, keyword hit rate, logprob top-1, optional LLM-as-Judge |

## Install

No `pip install` required in Phase 1. Just clone (already done if you're reading
this file) and run:

```bash
cd ai-obs-lab
cp config/proxy.example.yaml ~/.ai-obs-lab/proxy.yaml   # optional but recommended
$EDITOR ~/.ai-obs-lab/proxy.yaml                        # add CodeFuse / GLM URLs

bash start.sh           # starts proxy in background + live-tails summaries
bash start.sh report    # generates today's report and opens it
bash start.sh stop      # stops the background proxy
bash start.sh status    # show pid / log_dir / stderr file
```

If you prefer the explicit form:

```bash
PYTHONPATH=ai-obs-lab/src python3 -m ai_obs_lab.cli proxy
PYTHONPATH=ai-obs-lab/src python3 -m ai_obs_lab.cli eval --suite ... [--judge]
PYTHONPATH=ai-obs-lab/src python3 -m ai_obs_lab.cli report --date today --open
PYTHONPATH=ai-obs-lab/src python3 -m ai_obs_lab.cli tail
```

## 一键无感观测（推荐入口）

不想每次手动改环境变量？`bin/obs.sh` 提供零负担的包装命令：你照常用工具，
只是命令加 `-obs` 后缀，背后自动走代理、自动落盘，**原来的 `claude` / `cfuse`
命令完全不受影响**。

一次性安装（在 `~/.zshrc` 末尾加一行）：

```bash
echo 'source /Users/yushu/IdeaProjects/personalSkills/ai-obs-lab/bin/obs.sh' >> ~/.zshrc
source ~/.zshrc
```

然后像平时一样用：

```bash
claude-obs                      # 交互式 Claude Code，全程被观测
claude-obs -p "你的问题"         # 单次
cfuse-obs                       # 交互式 CodeFuse，全程被观测

obs report                      # 打开今天的 HTML 报告（含上下文面板）
obs tail                        # 实时看请求流水
obs status                      # 代理状态
obs stop                        # 停止后台代理
```

包装层做了三件事：自动确保代理在跑（不在则后台拉起）、把 `ANTHROPIC_BASE_URL`
指向代理（`claude` 用临时 settings 接管、`cfuse` 用 env 接管）、透传你的全部参数。
认证 token 由工具自己携带、代理原样转发，`obs.sh` 不持有你的密钥。

> CodeFuse(`cfuse`) 内核也是 Claude Code，走同一个 antchat 网关。代理为它单建
> 了 `cfuse` profile，只是为了让 trace 里 `upstream` 字段能区分 claude / cfuse。

---

## Plug your AI tool into the proxy

如果你想自己控制环境变量（不用上面的包装命令），可按下面手动接入。
The proxy listens on `127.0.0.1:8788` and routes by URL prefix. The real auth
header is passed through verbatim — `ai-obs-lab` does not own your API keys.

### A — Claude Code

```bash
export ANTHROPIC_BASE_URL=http://127.0.0.1:8788/anthropic
export ANTHROPIC_AUTH_TOKEN=<your real token>          # forwarded as-is
# Optional models / region settings stay the same.
```

For multi-profile setups (e.g. two Anthropic-compatible providers), reuse this
repo's existing [`claude-code-switcher`](../claude-code-switcher/) — add a `lab`
profile pointing at the proxy and you can flip in/out of observation mode in a
single command.

### B — Codex CLI

Edit `~/.codex/config.toml`:

```toml
openai_base_url = "http://127.0.0.1:8788/openai"
```

Or per-invocation:

```bash
OPENAI_BASE_URL=http://127.0.0.1:8788/openai codex ...
```

### C — CodeFuse / GLM / other OpenAI-compatible gateways

These show up in `proxy.yaml` under `upstreams.profiles`:

```yaml
upstreams:
  profiles:
    cfuse: https://your-cfuse-gateway.example.com
    glm:   https://open.bigmodel.cn/api/paas/v4
```

Then:

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8788/upstream/cfuse
# or
export OPENAI_BASE_URL=http://127.0.0.1:8788/upstream/glm
```

The path after `/upstream/<profile>/` is appended to the configured base URL.

## A/B evaluating a prompt

```bash
PYTHONPATH=ai-obs-lab/src python3 -m ai_obs_lab.cli eval \
  --suite ai-obs-lab/src/ai_obs_lab/eval/suites/json-extract.example.yaml \
  --repeat 10 --logprobs --judge
```

The bundled example suite compares a "loose" extraction prompt against a
"strict" one across two cases. The runner produces:

| Metric | Meaning |
|--------|---------|
| `similarity_variance` | `1 − mean pairwise SequenceMatcher ratio`. 0 = perfectly stable, 1 = wildly different |
| `schema_compliance_rate` | fraction of outputs whose extracted JSON validates against `expect_schema` |
| `keyword_hit_rate` | fraction containing all `expect_keywords` (case-insensitive) |
| `avg_logprob_top1` | mean `exp(logprob)` over chosen tokens (OpenAI-compatible upstreams only) |
| `avg_ttft_ms` / `avg_total_ms` / `avg_tokens_out` | latency & cost |
| LLM-as-Judge `correctness / format / conciseness / faithfulness` | 1-5 each (with `--judge`) |

Eval traces land in the same store and show up in the dashboard's **Evals** tab
side-by-side with a sample output diff.

Write your own suite — see `eval/suites/json-extract.example.yaml`. Required
keys: `name`, `upstream`, `model`, `versions[]`, `cases[]`.

## The dashboard

```bash
bash start.sh report           # today
PYTHONPATH=... python3 -m ai_obs_lab.cli report --date 2026-06-01 --open
PYTHONPATH=... python3 -m ai_obs_lab.cli report --date all --no-inline-details
```

Three tabs:

- **Traces** — KPI cards (count / errors / avg TTFT / token totals / tool
  calls) + a scrollable table. Click a row to see:
  - **Context（模型实际看到的全部内容）** — 这是理解 skill / MCP 的核心面板：
    - **token 占比条**：直观看到上下文被 system / tools / messages 各吃掉多少
    - **System prompt**：产品/工具注入的人设与规则全文
    - **Tools menu**：每个工具的 name + description + JSON Schema，**自动标注来源**
      （`MCP(server)` / `builtin` / `skill` / `other`）—— 这就是 skill / MCP
      暴露给模型的"菜单"，模型据此决定调用谁
    - **Messages**：历史消息分层，每条标注 role、token 估算、是否含
      `tool_use` / `tool_result`
  - the chunk timeline (text / tool_use / tool_args / pause / stop)，pause >800ms
    高亮 —— 看模型在哪个 token 处犹豫
  - tool-call JSON、redacted headers、完整 request body、response text
- **Evals** — per `eval_run_id` table: each case shows a per-version comparison
  of all objective metrics + judge scores + sample outputs.
- **Tools / MCP** — every captured `tool_use`, grouped by name, with parse-OK
  vs parse-fail counts and sample arguments.

The output is a single self-contained HTML file (data embedded as JSON). No
server, no fetch, opens with `file://`.

## Storage layout

```
~/.ai-obs-lab/
├── proxy.yaml                # your config (optional)
├── proxy.pid                 # bg pid (managed by start.sh)
├── proxy.stderr.log          # bg stderr
├── report.html               # latest generated report
└── logs/
    └── 2026-06-01/
        ├── summary.jsonl     # one TraceSummary per line
        ├── eval_runs.jsonl   # one EvalRun per line
        ├── judge_results.jsonl
        └── traces/
            ├── <trace_id>.json        # full TraceFull
            └── <trace_id>.body.json   # request body sidecar if >256KB
```

Wipe it any time: `rm -rf ~/.ai-obs-lab/logs`.

## Repo layout (Phase 1)

```
ai-obs-lab/
├── pyproject.toml                  # placeholder; Phase 2 enables [project.scripts]
├── SKILL.md
├── README.md                       # this file
├── start.sh
├── scripts/
│   └── extract_to_standalone.sh    # Phase 2 trigger; supports --dry-run
├── config/
│   └── proxy.example.yaml
├── src/ai_obs_lab/
│   ├── cli.py                      # python -m ai_obs_lab.cli {proxy|eval|report|tail|version}
│   ├── core/{models,store}.py
│   ├── proxy/{server,sse_parser}.py
│   ├── eval/{runner,judge,metrics}.py + suites/
│   └── dashboard/{query,html,tail}.py
└── tests/                          # stdlib unittest
```

## What's NOT here yet (Roadmap → Phase 2 candidates)

- **stdio MCP wrapper** — current proxy only catches HTTP-based MCP (e.g.
  WebSocket gateways). For stdio servers, wrap the binary with a small launcher
  that tees JSON-RPC frames to the store.
- **FastAPI Web UI** — `dashboard/query.py` is already pure and stdlib-only so
  Phase 2 just adds a thin FastAPI layer over it.
- **DuckDB/SQLite store** — `core.store.Store` is a Protocol; swap the
  implementation when JSONL gets too big to scan.
- **Parallel eval execution** — runner is currently sequential.
- **PromptFoo / OpenAI Evals interop** — import / export their suite schemas.

## Phase 2: how to extract

When the toolkit has proved itself:

```bash
cd ai-obs-lab
bash scripts/extract_to_standalone.sh --dry-run    # print plan
bash scripts/extract_to_standalone.sh              # real move
```

This:

1. Verifies `git status` is clean and destination is empty
2. `git mv` (or `mv`) the tree to `~/IdeaProjects/ai-obs-lab/`
3. Symlinks back into `personalSkills/ai-obs-lab` so existing skill
   registrations keep working
4. `git init` the new location and patch `pyproject.toml` to enable the
   `aolab` console script
5. Prints next-step hints (`pip install -e .`, `git remote add`, …)

## License

MIT (matches the parent repo).
