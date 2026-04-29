---
name: skill-store-manager
description: "本地 Skill 中央仓库 + 软链接分发管理工具。所有 skill 统一存放在中央仓库（默认 ~/.skill-store/store/），通过软链接分发到所有 AI 编程工具的 skills 目录。支持从本地路径/Git/private-npm/URL 安装 skill，支持反向归集（adopt）已有 skill，支持完整生命周期管理（install/uninstall/update/link/unlink/list/status/export/sync）。支持双 scope（global/project，团队协作 skills.txt）、Windows 自动降级到目录复制、pip requirements.txt 风格的批量管理。触发词：skill 中央仓库、skill store、统一管理 skill、本地 skill 仓库、安装 skill 到中央仓库、归集 skill、adopt skill、skillctl、skills.txt、批量安装 skill、项目级 skill、团队 skill。"
---

# Skill Store Manager

本地 Skill 中央仓库 + 软链接分发管理工具，类似 `pnpm store` 的设计。

## 触发场景

- "本地 skill 仓库" / "skill 中央仓库" / "skill store"
- "统一管理 skill" / "把 skill 都放到一起"
- "归集 skill" / "adopt skill" / "把现有 skill 收编到仓库"
- "安装 skill 到中央仓库"
- 提到 `skillctl` 命令

## 核心理念

```
┌──────────────────────────────────────────┐
│  中央仓库 ~/.skill-store/store/  (单一存储源) │
└──────────────┬───────────────────────────┘
               │ 软链接分发
   ┌───────────┼───────────┬─────────┐
   ▼           ▼           ▼         ▼
~/.claude   ~/.codex   ~/.cursor  ...10个工具
 /skills/    /skills/    /skills/
```

**优势**：
- 一处更新，所有工具同步生效
- 单一存储源，节省磁盘
- 完整生命周期：install / uninstall / update / list / link / unlink

## 快速开始

### 1. 检测本机已安装的 AI 工具

```bash
python3 scripts/skillctl.py detect          # 扫描 + 显示精简列表
python3 scripts/skillctl.py scan            # 通用扫描：含未知工具按路径推断
python3 scripts/skillctl.py scan --refresh  # 强制刷新扫描缓存
python3 scripts/skillctl.py scan --json     # 机器可读输出
```

> `detect` 与 `scan` 都基于通用扫描机制 —— **任何放在 `~/.xxx/**/skills/` 或 `~/.xxx/**/skill/` 下、且至少含一个 `SKILL.md` 子目录的目录都会被自动识别**，不再依赖硬编码工具白名单。已知工具显示官方友好名（"Claude Code"），未知工具按路径自动推断（如 `~/.codefuse/engine/cc/skills` → `codefuse-engine-cc`）。详见下文「通用扫描规则」。

### 2. 反向归集（推荐首次执行）

把已经散落在各 AI 工具下的真实 skill 目录全部收编到中央仓库，并替换为软链：

```bash
# 预览
python3 scripts/skillctl.py adopt --all --dry-run

# 执行（自动备份到 ~/.skill-store/backups/<timestamp>/）
python3 scripts/skillctl.py adopt --all
```

### 3. 多源安装新 skill

```bash
# 本地路径
python3 scripts/skillctl.py install ./my-skill

# Git 仓库
python3 scripts/skillctl.py install https://github.com/user/skill.git --ref main

# private-npm / npm 包（@scope/name 格式）
python3 scripts/skillctl.py install @your-scope/skill-name

# URL（zip / tar.gz）
python3 scripts/skillctl.py install https://example.com/skill.zip

# 只链接到指定工具
python3 scripts/skillctl.py install ./my-skill --targets claude-code,cursor
```

### 4. 列出

```bash
python3 scripts/skillctl.py list           # 中央仓库中所有 skill
python3 scripts/skillctl.py list --tools   # 各 AI 工具下现存 skill
```

### 5. 卸载 / 链接管理

```bash
python3 scripts/skillctl.py uninstall my-skill              # 完全卸载
python3 scripts/skillctl.py uninstall my-skill --keep-store # 只解链不删仓库
python3 scripts/skillctl.py link my-skill                   # 重建软链到所有工具
python3 scripts/skillctl.py unlink my-skill --targets cursor
```

### 6. 更新

```bash
python3 scripts/skillctl.py update my-skill   # 按 manifest 重新拉取
```

### 7. 状态查看

```bash
python3 scripts/skillctl.py status my-skill                          # 全局 scope（默认）
python3 scripts/skillctl.py status my-skill --scope project          # 仅项目级
python3 scripts/skillctl.py status my-skill --scope all              # 同时显示 global+project
python3 scripts/skillctl.py store                                    # 查看中央仓库信息
```

### 8. 双 scope（global vs project，团队协作）

```bash
# global（默认）：链接到 ~/.claude/skills/my-skill 等，仅当前用户可见
python3 scripts/skillctl.py link my-skill

# project：链接到 ./.claude/skills/my-skill 等，可入 git 与团队共享
python3 scripts/skillctl.py link my-skill --scope project --cwd /path/to/project
python3 scripts/skillctl.py install ./my-skill --scope project    # 安装即链接到项目

# both：同时链接到 global 和 project 两个 scope
python3 scripts/skillctl.py link my-skill --scope both
```

### 9. 批量管理（pip requirements.txt 风格）

```bash
# 把当前已安装的 skill 列表导出到 skills.txt（可入 git）
python3 scripts/skillctl.py export -o skills.txt
python3 scripts/skillctl.py export --no-comments        # 不含版本/类型注释
python3 scripts/skillctl.py export                      # stdout 输出

# 从 skills.txt 批量安装
python3 scripts/skillctl.py install skills.txt
python3 scripts/skillctl.py install skills.txt --dry-run
python3 scripts/skillctl.py install skills.txt --auto-link --scope project

# 从 skills.txt 批量同步到工具目录（不下载）
python3 scripts/skillctl.py sync skills.txt --scope project --cwd .
```

**skills.txt 格式**（pip requirements 风格）：
```text
# 团队公共 skill
https://github.com/foo/bar.git
@your-scope/skill-name
./local-skill                # 行内注释 OK
```

### 10. 链接策略：symlink vs copy（Windows 兼容）

```bash
# 自动模式（默认）：*nix → symlink，Windows → copy
python3 scripts/skillctl.py link my-skill

# 强制使用 copy（避免 Windows 软链权限问题，或调试场景）
python3 scripts/skillctl.py link my-skill --copy

# 强制使用 symlink
python3 scripts/skillctl.py link my-skill --symlink
```

也可以在 `~/.skill-store/config.json` 中设置默认策略：
```json
{ "link_strategy": "auto" }    // auto / symlink / copy
```

## 命令总览

| 命令 | 说明 |
|------|------|
| `install <source>` | 从 local/git/private-npm/url 安装到中央仓库并分发软链 |
| `uninstall <name>` | 卸载 skill 并清理所有软链 |
| `update <name>` | 按 manifest 中的来源重新拉取最新版 |
| `adopt --all` | 把工具目录现存真实 skill 反向归集到中央仓库 |
| `list [--tools]` | 列出中央仓库 / 各工具中的 skill |
| `link <name>` | 把中央仓库 skill 链接到工具 |
| `unlink <name>` | 从工具中移除链接（保留中央仓库） |
| `export [-o FILE]` | 把当前已安装的 skill 列表导出为 skills.txt（pip requirements 风格） |
| `sync <name\|file.txt>` | 把 skill 链接到工具目录（不下载）；`.txt` 时按 skills.txt 批量 |
| `detect` | 检测本机已安装的 AI 工具（精简列表） |
| `scan` | 通用扫描，展示全部识别到的 skills 目录（含未知工具的路径推断结果） |
| `store [--set PATH]` | 查看/设置中央仓库根路径 |
| `status <name>` | 查看 skill 在各工具中的链接状态（支持 `--scope global\|project\|all`） |

### 全局参数（多个命令通用）

| 参数 | 适用命令 | 说明 |
|------|---------|------|
| `--scope {global,project,both,all}` | install / link / unlink / sync / status | scope 选择，默认 global；status 支持 all |
| `--cwd PATH` | install / link / unlink / sync / status | project scope 时的项目根（默认 `$PWD`） |
| `--copy` | install / link / sync | 强制使用目录复制（覆盖 link_strategy） |
| `--symlink` | install / link / sync | 强制使用 symlink（覆盖 link_strategy） |
| `--targets a,b,c` | install / link / unlink / sync | 仅作用于指定工具（逗号分隔） |
| `--auto-link` | install（批量） | 批量安装时自动 link 到工具目录 |
| `--dry-run` | install / link / unlink / sync / uninstall | 预览不写入 |

## 通用扫描规则

本工具不再硬编码工具白名单 —— 任何符合以下条件的目录都会被自动识别为「某 AI 工具的 skills 目录」：

1. **位置**：位于 `~/` 下首层以 `.` 开头的隐藏目录中
2. **深度**：从 `~/` 起算 ≤ 4 层（可通过 `scan --max-depth N` 调整）
3. **目录名**：必须是 `skills` 或 `skill`
4. **内容**：至少有一个子目录包含 `SKILL.md`（避免误识别空目录；可通过 `scan --include-empty` 放宽）
5. **黑名单**：自动跳过 `.git/.Trash/.cache/.npm/.node_modules/.vscode/.idea/.docker/.Steam/.Spotify/.ssh/.gnupg` 等噪音目录

### 工具识别策略

扫到的目录按"**已知别名优先 → 路径推断兜底**"的方式生成 `tool_key` 与友好名：

**已知别名表**（命中后显示官方友好名）：

| 友好名 | tool_key | 路径 |
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

**未命中别名时按路径推断**：取 `~/` 之后到 `skills` 之间的路径段，去掉首字符 `.`，用 `-` 连接：

| 真实路径 | 推断 tool_key | 推断 name |
|---|---|---|
| `~/.foo/skills` | `foo` | `Foo` |
| `~/.codefuse/engine/cc/skills` | `codefuse-engine-cc` | `Codefuse Engine Cc` |
| `~/.qoder/skills` | `qoder` | `Qoder` |

> 推断结果在 `scan` 输出中标记为「🔮 推断」，别名命中标记为「🏷  别名」，便于你检视识别质量。
> 如果识别不理想，可通过 `~/.skill-store/config.json` 的 `scan.extra_aliases` 自定义补充别名。

## 支持的 AI 工具（本机自动检测）

`scan` 命令会列出**本机实际存在**的所有 skills 目录，例如典型环境下可能识别到 20+ 个工具（10 个已知别名 + 10+ 个按路径推断的工具）。运行 `python3 scripts/skillctl.py scan` 查看你机器上的实际结果。

## 中央仓库布局

```
~/.skill-store/                    # 默认根（可被 SKILL_STORE_HOME 覆盖）
├── config.json                    # 全局配置
├── store/                         # skills 实际存储
│   ├── skill-a/
│   └── skill-b/
├── manifest.json                  # 元数据
└── backups/<timestamp>/           # adopt 时的原数据备份
```

### manifest.json schema (v2.1)

```json
{
  "version": "2.1",
  "store_path": "/Users/xxx/.skill-store/store",
  "skills": {
    "my-skill": {
      "version": "1.0.0",
      "source": {
        "type": "git|private-npm|local|url|adopted",
        "ref": "https://... | @your-scope/xxx | /path"
      },
      "installed_at": "2026-04-28T...",
      "updated_at": "2026-04-28T...",
      "linked_targets": [
        {"tool_key": "claude-code", "scope": "global", "link_type": "symlink"},
        {"tool_key": "cursor",      "scope": "global", "link_type": "symlink"},
        {"tool_key": "claude-code", "scope": "project", "link_type": "symlink",
         "project_root": "/Users/xxx/IdeaProjects/foo"}
      ]
    }
  }
}
```

> **schema 兼容**：v2.0 的 `linked_targets: ["claude-code", "cursor"]`（字符串数组）会在加载时自动归一化为 v2.1 的 dict 形态（默认 `scope=global, link_type=symlink`），下次保存时升 version。无需手动迁移。

## 自定义中央仓库路径

```bash
# 临时（环境变量优先级最高）
SKILL_STORE_HOME=/data/skills python3 scripts/skillctl.py list

# 持久化
python3 scripts/skillctl.py store --set /data/skills
```

## 链接状态说明

| 状态 | 含义 |
|------|------|
| ✅ linked | 软链接正确指向中央仓库（或 `--copy` 模式下的真实复制目录） |
| ❌ other | 软链接指向其他源（需重新 link） |
| ⚠️ real | 真实目录（建议 adopt 归集） |
| - none | 工具已安装但未链接 |
| · missing | 工具未安装（已跳过） |

`status` 命令额外列：
- **scope**：`global` / `project`
- **链接类型**：`symlink` / `copy`

## 冲突处理

- **install 时中央仓库已存在同名 skill** → 报错，需 `--force` 覆盖
- **链接时目标位置已是真实目录** → 跳过并提示用 `adopt` 归集
- **adopt 时中央仓库已存在同名** → 跳过并提示，需 `--overwrite` 覆盖

## 与 skill-debug-sync 的关系

`skill-debug-sync` 是仅做软链同步的轻量工具，本工具是其超集，**完全独立、不修改它**。
两者可共存。已使用 `skill-debug-sync` 的用户可执行 `adopt --all` 把现有 skill 归集到本工具。

## Hard Rules

1. 始终使用中文回答
2. 反向归集（adopt）默认会备份到 `~/.skill-store/backups/<timestamp>/`，除非 `--no-backup`
3. install / uninstall / adopt 的破坏性操作支持 `--dry-run` 先预览
4. 不修改 `~/.claude/skills/skill-debug-sync/` 的任何内容
5. 中央仓库根路径优先级：`SKILL_STORE_HOME` 环境变量 > `config.json` 中 `store_home` > 默认 `~/.skill-store`
6. 输出简洁，只展示已检测到的工具
