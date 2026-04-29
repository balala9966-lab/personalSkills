# skill-store-manager

> 本地 Skill 中央仓库 + 软链接分发管理工具

类似 `pnpm store` 的设计：所有 skill 统一存放在中央仓库 `~/.skill-store/store/`，
通过软链接分发到各 AI 编程工具（Claude Code / Codex / Cursor / Windsurf / CodeFuse 等）的 skills 目录。

## 特性

- 📦 **中央仓库**：单一存储源，节省磁盘，便于统一升级
- 🔗 **软链接分发**：一处更新，所有工具同步生效
- 🌐 **多源安装**：本地路径 / Git / private-npm / URL zip
- 📥 **反向归集（Adopt）**：把已散落在各工具下的 skill 收编到中央仓库
- 🛠 **完整生命周期**：install / uninstall / update / list / link / unlink / export / sync
- 🔍 **状态可视**：随时查看任一 skill 在各工具下的链接状态
- 👥 **双 scope（global / project）**：个人级 + 团队项目级，支持入 git 共享
- 📋 **批量管理（skills.txt）**：pip requirements.txt 风格，一键 export / install
- 🪟 **跨平台**：支持 macOS / Linux 软链；Windows 自动降级到目录复制（也可 `--copy` 强制）

## 快速开始

```bash
# 1. 检测本机已安装的 AI 工具
python3 scripts/skillctl.py detect       # 精简列表
python3 scripts/skillctl.py scan         # 通用扫描（含未知工具的路径推断结果）

# 2. 反向归集：把已有的 skill 全部收编到中央仓库
python3 scripts/skillctl.py adopt --all --dry-run    # 预览
python3 scripts/skillctl.py adopt --all              # 执行

# 3. 安装新 skill（多源）
python3 scripts/skillctl.py install ./my-skill                    # 本地
python3 scripts/skillctl.py install https://github.com/x/y.git    # Git
python3 scripts/skillctl.py install @your-scope/skill-name        # private-npm
python3 scripts/skillctl.py install https://example.com/x.zip     # URL

# 4. 列出
python3 scripts/skillctl.py list           # 中央仓库
python3 scripts/skillctl.py list --tools   # 各工具下

# 5. 卸载
python3 scripts/skillctl.py uninstall my-skill

# 6. 查看某 skill 在所有工具下的状态
python3 scripts/skillctl.py status my-skill                          # global
python3 scripts/skillctl.py status my-skill --scope all              # global + project
```

## 团队协作（双 scope + skills.txt）

```bash
# 团队负责人：把当前 skill 列表导出到项目，入 git
python3 scripts/skillctl.py export -o skills.txt
git add skills.txt && git commit -m "add team skills"

# 新成员：拉项目后一键拉齐
git clone <repo> && cd <repo>
python3 scripts/skillctl.py install skills.txt --scope project --auto-link
```

```bash
# 项目级 skill（仅当前项目可见，链接到 ./.claude/skills/）
python3 scripts/skillctl.py link my-skill --scope project --cwd .

# 全局个人级 skill（链接到 ~/.claude/skills/）
python3 scripts/skillctl.py link my-skill                         # 默认 scope=global

# 同时双 scope 链接
python3 scripts/skillctl.py link my-skill --scope both
```

## 跨平台（symlink ↔ copy）

```bash
# 默认 auto：*nix 用 symlink，Windows 自动降级到目录复制
python3 scripts/skillctl.py link my-skill

# 强制使用复制（Windows、有软链权限问题、或调试场景）
python3 scripts/skillctl.py link my-skill --copy

# 持久化默认策略
# 编辑 ~/.skill-store/config.json: { "link_strategy": "copy" }
```

## 中央仓库布局

```
~/.skill-store/                    # 默认根目录（可通过 SKILL_STORE_HOME 覆盖）
├── config.json                    # 全局配置
├── store/                         # skills 实际存储
│   ├── skill-a/
│   ├── skill-b/
│   └── ...
├── manifest.json                  # 元数据
└── backups/                       # adopt 时的原数据备份
    └── <timestamp>/
```

## 支持的 AI 工具

本工具采用**通用扫描机制**，不依赖硬编码工具白名单：

- **扫描规则**：自动识别 `~/.xxx/**/skills/` 或 `~/.xxx/**/skill/`（深度 ≤ 4），且至少包含一个含 `SKILL.md` 的子目录
- **已知工具**显示官方友好名（如 "Claude Code"），未知工具按路径自动推断（如 `~/.codefuse/engine/cc/skills` → `codefuse-engine-cc`）
- 运行 `python3 scripts/skillctl.py scan` 查看本机实际识别到的所有工具

**已知别名表**（共 12 条，命中后显示官方友好名）：

| 工具 | tool_key | 安装路径 |
|------|----------|----------|
| Claude Code | `claude-code` | `~/.claude/skills` |
| Codex CLI (OpenAI) | `codex-cli` | `~/.codex/skills` |
| Codex Engine | `codex-engine` | `~/.codefuse/engine/codex/skills` |
| CodeFuse Engine CC | `codefuse` | `~/.codefuse/engine/cc/skills` |
| CodeFuse Fuse | `codefuse-fuse` | `~/.codefuse/fuse/skills` |
| Windsurf | `windsurf` | `~/.codeium/windsurf/skills` |
| OpenClaw | `openclaw` | `~/.openclaw/workspace/skills` |
| OpenCode | `opencode` | `~/.opencode/skills` |
| Homiclaw | `homiclaw` | `~/.homiclaw/workspace/user-skills` |
| Homiclaw Gateway | `homiclaw-gateway` | `~/.homiclaw/gateway-bundle/skills` |
| Agents | `agents` | `~/.agents/skills` |
| Cursor | `cursor` | `~/.cursor/skills` |

> 任何**未在上表中的 AI 工具**，只要它把 skills 放在 `~/.<tool>/.../skills/` 结构下，本工具也能自动识别并管理。

## 自定义中央仓库路径

```bash
# 临时
SKILL_STORE_HOME=/data/skills python3 scripts/skillctl.py list

# 持久化
python3 scripts/skillctl.py store --set /data/skills
```

## 与 skill-debug-sync 的关系

`skill-debug-sync` 是仅做软链同步的轻量工具，本工具是其超集，**不依赖也不修改它**，
两者可共存。已经使用 `skill-debug-sync` 的用户可以直接 `adopt --all` 把现有 skill
归集到本工具的中央仓库。

## 安装为可执行命令

```bash
# 软链到 PATH
ln -s "$(pwd)/scripts/skillctl.py" /usr/local/bin/skillctl
chmod +x /usr/local/bin/skillctl

# 之后即可：
skillctl detect
skillctl install ./my-skill
```

## License

MIT
