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
├── skill-store-manager/         # 中央 skill 仓库管理
├── skill-debug-sync/            # 本地 skill 调试软链
├── claude-code-switcher/        # Claude Code 双平台 settings.json 切换
└── knowledge-wiki/              # LLM Wiki + 代码知识库
```

## License


