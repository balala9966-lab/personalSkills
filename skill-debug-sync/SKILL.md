---
name: skill-debug-sync
description: "一键将 skill 同步到所有已安装的 AI 编程工具。自动检测本机 skills 目录，按名称查找 skill 并创建软连接实现跨平台调试。触发词：调试skill、同步skill、link skill、sync skill。"
---

# Skill Debug Sync

一键将本地 skill 同步到所有已安装的 AI 编程工具，实现跨平台调试。

## 触发场景

- "调试 skill" / "调试技能"
- "同步 skill" / "skill 同步"
- "link skill" / "sync skill"

## 快速开始

```bash
# 在 skill 目录下运行，自动检测并同步
python3 scripts/sync_skill.py

# 按名称查找并同步
python3 scripts/sync_skill.py --skill my-skill

# 检测本机有哪些 skills 目录
python3 scripts/sync_skill.py --detect-dirs

# 列出所有已安装的 skill
python3 scripts/sync_skill.py --list-skills
```

## 支持的 Skills 目录

| 工具 | Skills 目录 |
|------|-------------|
| Claude Code | `~/.claude/skills` |
| Codex CLI | `~/.codex/skills` |
| Codex Engine | `~/.codefuse/engine/codex/skills` |
| CodeFuse | `~/.codefuse/engine/cc/skills` |
| Windsurf | `~/.codeium/windsurf/skills` |
| OpenClaw | `~/.openclaw/workspace/skills` |
| OpenCode | `~/.opencode/skills` |
| Homiclaw | `~/.homiclaw/workspace/user-skills` |
| Agents | `~/.agents/skills` |

## 命令选项

```bash
# 基本用法
python3 scripts/sync_skill.py                    # 自动检测当前目录的 skill
python3 scripts/sync_skill.py /path/to/skill     # 指定 skill 目录
python3 scripts/sync_skill.py --skill <name>     # 按名称查找并同步

# 检测和列表
python3 scripts/sync_skill.py --detect-dirs      # 检测本机 skills 目录
python3 scripts/sync_skill.py --list-skills      # 列出所有已安装的 skill
python3 scripts/sync_skill.py --status           # 查看同步状态
python3 scripts/sync_skill.py --status --skill <name>  # 按名称查看状态

# 其他操作
python3 scripts/sync_skill.py --dry-run          # 预览模式
python3 scripts/sync_skill.py --unlink           # 删除软连接
```

## Skill 查找优先级

使用 `--skill <name>` 时，按以下顺序查找：

1. **当前工作目录**：检查 cwd 及其子目录
2. **Manifest 记录**：`~/.claude/skills/.skills-manifest.json`
3. **本机 skills 目录**：扫描所有检测到的 skills 目录

## 版本管理

版本号从 `package.json` 的 `version` 字段读取，同步时显示。

## 同步状态

| 状态 | 含义 |
|------|------|
| ✅ 已同步 | 符号链接正确指向源目录 |
| ⚠️ 真实目录 | 目标路径存在真实目录（非链接），需手动处理 |
| ❌ 指向其他源 | 链接指向其他 skill，需重新同步 |
| - 未链接 | 目录存在但未创建链接 |

## 工作原理

1. **检测目录**：扫描本机所有已配置的 skills 目录
2. **查找 skill**：按优先级查找用户指定的 skill 源目录
3. **创建软连接**：在所有检测到的目录中创建软连接
4. **更新 Manifest**：记录同步信息便于后续查找

## 注意事项

- 目标位置存在同名真实目录时跳过
- 软连接会覆盖指向不同目标的已有链接
- 已正确链接的 skill 显示 "Already linked" 并跳过

## Hard Rules

1. 始终使用中文回答
2. 同步前检测本机 skills 目录是否存在
3. 按 cwd → manifest → skills 目录的优先级查找 skill
4. 同步成功后更新 Manifest 记录
5. 删除操作只删除指向正确源的符号链接
6. 输出简洁，仅展示可用信息