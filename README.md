# personalSkills

A collection of personal AI agent skills for Claude Code, Cursor, Codex, Windsurf and other AI coding tools.

> [!IMPORTANT]
> **面试陪练系统已迁移到独立仓库**：<https://github.com/balala9966-lab/interviewCoaching>
> 此仓库不再包含 `interview-coach-agent/` / `interview-skills/` / `test-dev-coach/` / `web/` / `start.sh`。
> 详见独立仓库的 [README](https://github.com/balala9966-lab/interviewCoaching#readme) 与 [CHANGELOG](https://github.com/balala9966-lab/interviewCoaching/blob/main/CHANGELOG.md)。

## Components

### Skill 管理基础设施

| 组件 | 说明 |
|------|------|
| [`skill-store-manager`](./skill-store-manager) | 中央 skill 仓库 + 软链接分发。支持多 AI 工具、双 scope（global/project）、`skills.txt` 批量管理、Windows 兼容降级。 |
| [`skill-debug-sync`](./skill-debug-sync) | 单 skill 一键软链到本机所有已安装的 AI 编程工具，用于本地调试。 |
| [`claude-code-switcher`](./claude-code-switcher) | Claude Code 双平台一键切换：通过 python3 改 `~/.claude/settings.json` 中的 `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL`，绕过"settings.json env 覆盖 shell env"的限制。`config-example.sh` 是模板。 |

### 知识库 / 内容工程

| 组件 | 说明 |
|------|------|
| [`knowledge-wiki`](./knowledge-wiki) | 融合 Karpathy LLM Wiki 方法论与代码仓库深度分析的统一知识库构建器，三层架构（Raw / Wiki / Schema），支持 qmd 语义检索。 |

### AI 可观测性

| 组件 | 说明 |
|------|------|
| [`ai-obs-lab`](./ai-obs-lab) | 本地 AI 可观测性实验台：stdlib HTTP 代理抓取 Claude Code / Codex / CodeFuse 与模型的完整交互（含 SSE 流式 chunk 时序、tool_calls、MCP），prompt A/B 评测（含可选 LLM-as-Judge），单文件 HTML 看板。阶段二可一键抽离独立工程。 |

### 文章配图系统（5 个 skill 协作）

| 组件 | 说明 |
|------|------|
| [`illustration-prompt-composer`](./illustration-prompt-composer) | **编排层**：读文档 → 分析 → 出 outline → 写 prompt → 调出图 → 回填。支持 markdown / 语雀公网 / 纯文本。三种模式：illustration / cover / both。 |
| [`illustration-image-backend`](./illustration-image-backend) | **后端层**：可插拔的图片生成 adapter。本仓库版本支持 OpenAI Images、OpenAI 兼容代理（Azure / OpenRouter / LiteLLM）、Google Gemini Imagen 三种公网后端。 |
| [`illustration-styles`](./illustration-styles) | **知识库层**：23 种 style × 6 种 type × 13 种 palette × 21 个 preset + 兼容矩阵 + 自动推荐规则。纯文档，无可执行代码。 |
| [`editorial-illustration`](./editorial-illustration) | **风格专用 skill**：高保真手绘 editorial 风格 + 默认 IP "The Tinkerer" + 构图模式词典 + QA 清单。独立使用或被 composer 引用。 |
| [`generate-image-public`](./generate-image-public) | **独立公网出图工具**：单文件 Python 脚本，走 OpenAI Images API，零 pip 依赖。 |

> **注**：另有一套内网版本（含额外出图后端和内网语雀回写支持），与本仓库公网版**功能等价但后端不同**。本仓库**不包含任何内网专用代码**。

**典型调用链**（给 md 文章配图）：

```
用户："给这篇 article.md 配图，技术风格"
  ↓
illustration-prompt-composer.run
  ├─ markdown ingester 读文章
  ├─ analyze.py 识别 content_type=technical
  ├─ 查 illustration-styles 推荐 preset=tech-explainer
  ├─ plan.py 产出 outline.md（type=infographic + style=blueprint）
  ├─ compose.py 产出每张图的 prompts/NN-*.md
  ├─ dispatch.py × N 次：subprocess 调 illustration-image-backend/scripts/generate.py
  │    └─ illustration-image-backend 路由到 openai_images / gemini / openai_compat
  ├─ writeback.py 把 ![](path) 写回 article.md
  └─ 完成
```

### 面试陪练系统（已迁出）

面试陪练系统（Agent + 5 Skill + Web/CLI 混合架构）已抽取为独立项目，请见：

🔗 <https://github.com/balala9966-lab/interviewCoaching>

```bash
# 一键克隆 + 启动
git clone https://github.com/balala9966-lab/interviewCoaching.git
cd interviewCoaching
./start.sh
```

或一键远程安装：

```bash
curl -fsSL https://raw.githubusercontent.com/balala9966-lab/interviewCoaching/main/install.sh | bash
```

## Quick Start

每个 skill 都有自己的 `SKILL.md`（与 `README.md`）。先把要用的 skill 软链到 AI 工具。

```bash
python3 skill-debug-sync/scripts/sync_skill.py knowledge-wiki

# 也可以用中央仓库统一管理:
python3 skill-store-manager/scripts/skillctl.py --help
```

## Repository Layout

```
personalSkills/
├── README.md
├── .gitignore
├── skill-store-manager/              # 中央 skill 仓库管理
├── skill-debug-sync/                 # 本地 skill 调试软链
├── claude-code-switcher/             # Claude Code 双平台 settings.json 切换
├── knowledge-wiki/                   # LLM Wiki + 代码知识库
├── illustration-prompt-composer/     # 文章配图：编排层
├── illustration-image-backend/       # 文章配图：出图后端调度（公网版）
├── illustration-styles/              # 文章配图：风格知识库
├── editorial-illustration/           # 文章配图：editorial 手绘专用风格
└── generate-image-public/            # 独立 OpenAI 出图脚本
```

## License


