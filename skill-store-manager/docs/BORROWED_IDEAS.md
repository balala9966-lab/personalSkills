# 借鉴 agent-skills-hub 的设计

> 调研时间：2026-04-28
> 参考项目：[youzaiAGI/agent-skills-hub](https://github.com/youzaiAGI/agent-skills-hub)
> 本机参考路径：`<本地 clone 的 agent-skills-hub 目录>`

本文档记录我们调研 `agent-skills-hub`（以下简称 ASH）后的对比分析、借鉴决策与未落地项的 roadmap，作为永久决策记录。

---

## 1. 项目对比一览

| 维度 | **agent-skills-hub**（社区） | **skill-store-manager**（本项目） |
|---|---|---|
| **核心定位** | 技能**包管理器** + **市场**（类 pip） | 中央**仓库** + **软链分发**（类 pnpm store） |
| **存储模型** | `~/.skill-hub/<owner>/<repo>/<skill>/` 按 GitHub repo 分组 | `~/.skill-store/store/<skill>/` 扁平化 |
| **同步方式** | 软链 + Windows 自动降级到目录复制 | 软链（本次新增 Windows 降级） |
| **Agent 配置** | `agent_cmd.py` 硬编码 18+ 工具，区分**项目级 + 全局级双路径** | 通用扫描机制 + 12 条已知别名表（本次新增 project_dir） |
| **来源** | 仅 GitHub repo（`owner/repo` 格式） | 多源：local / git / private-npm / url-zip |
| **批量管理** | ✅ `skill list > skills.txt` + `install skills.txt` 像 requirements.txt | ✅（本次新增） |
| **TUI 交互** | ✅ 完整 curses TUI（search 30KB / manage 27KB） | ❌（roadmap） |
| **自定义仓库** | ✅ `skill repo add/rm` | ❌（roadmap） |
| **跨平台** | ✅ Win/Linux/macOS | ✅（本次补齐 Windows 降级） |
| **反向归集** | ❌ | ✅ `adopt --all` |
| **链接状态可视化** | manage TUI 内 | ✅ `status` 命令 |

---

## 2. 已落地的借鉴点

### 2.1 双 scope（project / global） ✅ 已落地（v2.1）

**借鉴自**：ASH 的 `agent_cmd.py`，每个 Agent 都有项目级 + 全局级双路径

```python
# ASH 的设计
"ClaudeCode": [".claude/skills",  "~/.claude/skills"]
                ↑ 项目级 cwd 下      ↑ 全局 home 下
```

**本项目落地方式**（已实现）：

- `lib/tools.py`：`KNOWN_TOOL_ALIASES` 12 条全部新增 `project_dir` 字段（相对路径）
- `lib/tools.py`：新增 `discover_project_skill_dirs(cwd)` 扫描 `<cwd>/.xxx/skills/`
- `lib/tools.py`：新增 `get_tool_dir(tool_key, scope, cwd)` 统一入口
- `lib/tools.py`：`discover_skill_dirs(scope='global'|'project', cwd=...)` 按 scope 扫描
- `lib/linker.py`：`create_link / remove_link / link_to_all / unlink_from_all / get_link_status / get_currently_linked_targets` 全部接受 `scope` / `cwd` / `link_type`
- `scripts/skillctl.py`：`install / link / unlink / sync / status` 全部支持 `--scope {global,project,both,all}` 和 `--cwd PATH`

**实际可用命令**：

```bash
# 个人全局技能（默认）
skillctl link my-skill                                # → ~/.claude/skills/my-skill

# 团队项目级技能（入 git，团队共享）
skillctl link my-skill --scope project --cwd .        # → ./.claude/skills/my-skill

# 同时双 scope 链接
skillctl link my-skill --scope both

# 同时显示两个 scope 的状态
skillctl status my-skill --scope all
```

**测试覆盖**：`test_basic.sh` case 15（项目级 link/unlink/status）+ case 16（`--copy` 项目级）。

### 2.2 skills.txt 批量管理（pip requirements.txt 风格） ✅ 已落地（v2.1）

**借鉴自**：ASH 的 `skill list > skills.txt` + `skill install skills.txt`

**本项目落地方式**（已实现）：

- 新增 `lib/batch.py` 模块（332 行），核心 API：
  - `parse_requirements_file(path)`：解析 skills.txt，剥离行内注释
  - `export_skills_txt(out_path, include_comments)`：从 manifest 导出
  - `install_from_file(file_path, ..., dry_run, force, auto_link, link_scope, link_cwd, link_type)`：批量安装
  - `sync_from_file(file_path, scope, cwd, targets, link_type, dry_run)`：批量同步
- `scripts/skillctl.py`：
  - `cmd_install` 检测 `.txt` 后缀，走批量分支（`_cmd_install_batch` + `_print_batch_result`）
  - 新增 `cmd_export` + `export` 子命令（`-o`/`--no-comments`）
  - 新增 `cmd_sync` + `sync` 子命令（兼容单个 skill 名 / `.txt` 文件）

**实际可用命令**：

```bash
# 导出（pip requirements 风格，含 # 注释）
skillctl export -o skills.txt
skillctl export --no-comments        # 纯净格式
skillctl export                      # stdout 输出

# 批量安装
skillctl install skills.txt
skillctl install skills.txt --dry-run
skillctl install skills.txt --auto-link --scope project --cwd .

# 批量同步（不下载，仅 link）
skillctl sync skills.txt --scope project --cwd . --targets claude-code
```

**skills.txt 格式**（pip 兼容风格）：

```text
# 团队公共 skill
https://github.com/foo/bar.git
@your-scope/skill-name
./local-skill                        # 行内注释 OK
# 注释行 / 空行 / 行内注释 全部支持
```

- `#` 开头为注释，空行忽略
- 行内 `# xxx` 自动剥离
- 每行一个 source，自动嗅探类型（local/git/private-npm/url）
- 复用 `sources.detect_source_type()`，无需引入新格式

**典型工作流**：

```bash
# 项目 A 导出
skillctl export -o skills.txt
git add skills.txt && git commit -m "add team skills"

# 新成员/新机器
git pull
skillctl install skills.txt --scope project --auto-link
```

**测试覆盖**：`test_basic.sh` case 13（export）+ case 14（install via .txt），`test_batch.sh` B1-B9 端到端（25+ 断言）。

### 2.3 Windows 自动降级到目录复制 ✅ 已落地（v2.1）

**借鉴自**：ASH `v1.5.1` 的关键改进

**本项目落地方式**（已实现）：

- `lib/linker.py`：新增 `LINK_TYPE_SYMLINK` / `LINK_TYPE_COPY` / `LINK_TYPE_AUTO` 常量
- `lib/linker.py`：`_strategy(explicit='auto')` 决策函数
  - `explicit='symlink' / 'copy'` → 直接采用
  - 否则查 `config.link_strategy`（默认 `auto`）
  - 否则按平台：`sys.platform == 'win32'` → `copy`，其他 → `symlink`
- `lib/linker.py`：`create_link` 接受 `link_type='auto'|'symlink'|'copy'`
  - copy 走 `shutil.copytree`
  - symlink 失败（如 Windows 权限不足）自动 `OSError` → 降级为 copy
- `lib/linker.py`：`remove_link` 自动识别目标类型（`os.path.islink` 判断），分别用 `unlink` / `rmtree`
- `lib/manifest.py`：`linked_targets` 每条记录 `link_type`，卸载时无需依赖文件系统判断
- `lib/config.py`：新增 `link_strategy` 字段（auto/symlink/copy）
- `scripts/skillctl.py`：`install / link / sync` 新增 `--copy` / `--symlink` 标志覆盖默认策略

**实际可用命令**：

```bash
# 自动模式（默认）
skillctl link my-skill                       # *nix → symlink, Win → copy

# 强制 copy（Win 兼容、无权限场景）
skillctl link my-skill --copy

# 强制 symlink
skillctl link my-skill --symlink
```

**测试覆盖**：`test_basic.sh` case 16（`--copy` 创建真实目录而非软链 + uninstall 正确清理）。

---

## 3. 未落地的借鉴点（roadmap）

### 3.1 仓库级安装（一个 git repo 多个 skill）

**ASH 行为**：

```bash
skill install anthropic/python-tools         # 装整个 repo 下所有 skill
skill install web-debugger@anthropic/tools   # 装单个 skill
```

**未落地原因**：

- 我们的 `sources.install_from_git` 当前只识别第一个含 `SKILL.md` 的子目录
- 改造涉及 `sources.py` 的 `_find_skill_root` → `_find_all_skill_roots`，及 `store` / `manifest` 的批量入库
- 工作量约 1 天，价值中等（取决于用户是否常装包含多个 skill 的 repo）

**未来落地建议**：

- 在 `install_from_git / install_from_url / install_from_private_npm` 中新增 `multi_skill: bool = False` 参数
- `skillctl install <repo> --all-skills` 触发批量
- manifest 中标记 `parent_repo` 字段建立同源关系

### 3.2 TUI 交互界面

**ASH 行为**：`skill search` / `skill manage` 用 curses 提供方向键浏览、字母键过滤、Enter 安装

**未落地原因**：

- 我们的目标用户主要是 LLM Agent（CLI + JSON 输出已满足）
- TUI 主要服务"人眼浏览"场景，ROI 偏低
- 工作量 3-5 天

**未来落地建议**：

- 如果 `skillctl` 用户量上来，可以包装现有 CLI + JSON 输出做一个独立的 `skillctl-tui` 命令
- 优先做 `manage` 视图（已安装 skill 一览 + 状态 + 操作菜单），不做 `search`（市场场景与本项目定位无关）

### 3.3 自定义仓库管理（`skill repo add/rm`）

**ASH 行为**：维护一个用户级"已知仓库"列表，方便后续按仓库快速安装

**未落地原因**：本项目已有更通用的 `sources.install` 多源能力，单独的 `repo` 概念意义不大

---

## 4. 我们保留的优势（不向社区项目让步的设计）

| 优势 | 本项目做法 | ASH 做法 |
|---|---|---|
| **通用扫描机制** | 自动识别任意 `~/.xxx/**/skills/`，未知工具按路径推断 | 18 个 Agent 全部硬编码在 `agent_cmd.py`，加新工具要改源码发版 |
| **多源安装** | local / git / private-npm / url-zip | 仅 GitHub `owner/repo` |
| **adopt 反向归集** | 一键收编已散落的真实 skill 到中央仓库 + 自动备份 | 无此能力 |
| **链接状态机** | `LINK_STATUS_LINKED/OTHER_SOURCE/REAL_DIR/NOT_LINKED/TOOL_MISSING` 5 态可视化 | manage TUI 内有但不够细 |
| **中央仓库 + 软链架构** | pnpm store 模型，单一存储源 | 也是中央仓库，但路径绑死 `~/.skill-hub` |
| **配置可扩展** | `~/.skill-store/config.json` + `scan.extra_aliases` 用户可自定义 | 没有用户配置层 |

---

## 5. 借鉴 ROI 评估

| 借鉴点 | 工作量 | 用户价值 | 落地状态 |
|---|---|---|---|
| 双 scope（project/global） | 1 天 | 🔴 高（团队协作刚需） | ✅ 已落地 |
| skills.txt 批量管理 | 0.5 天 | 🔴 高（团队协作刚需） | ✅ 已落地 |
| Windows 自动降级 | 0.5 天 | 🟡 中（取决于是否需 Win 用户） | ✅ 已落地 |
| 仓库级安装 | 1 天 | 🟡 中（视用户来源） | 🚧 roadmap |
| TUI 交互 | 3-5 天 | 🟢 低（LLM Agent 场景已满足） | 🚧 roadmap |

---

## 6. 命令对照表（ASH ↔ 本项目）

| ASH | 本项目（落地后） | 说明 |
|---|---|---|
| `skill install <pkg>` | `skillctl install <source>` | 本项目 source 类型更宽 |
| `skill install skills.txt` | `skillctl install skills.txt` | ✅ 本次新增 |
| `skill list > skills.txt` | `skillctl export -o skills.txt` | ✅ 本次新增 |
| `skill sync <agent> <skill> -p` | `skillctl link <skill> --scope project` | ✅ 本次新增（语义合并） |
| `skill sync <agent> <skill> -g` | `skillctl link <skill> --scope global` | 默认 scope=global，向后兼容 |
| `skill sync <agent> skills.txt -p` | `skillctl sync skills.txt --scope project` | ✅ 本次新增 |
| `skill manage` | `skillctl status <name> --scope all` | 文本视图替代 TUI |
| `skill repo add/rm` | （无）→ 直接用 `install <source>` | 不引入 repo 概念 |
| `skill search` | （无） | 不做市场场景 |

---

## 7. Schema 变更记录

### manifest.json：v2.0 → v2.1

```diff
 {
-  "version": "2.0",
+  "version": "2.1",
   "skills": {
     "my-skill": {
       "version": "1.0.0",
       "source": {"type": "git", "ref": "..."},
-      "linked_targets": ["claude-code", "cursor"]
+      "linked_targets": [
+        {"tool_key": "claude-code", "scope": "global", "link_type": "symlink"},
+        {"tool_key": "claude-code", "scope": "project", "link_type": "symlink",
+         "project_root": "/path/to/your/project/foo"}
+      ]
     }
   }
 }
```

**兼容策略**：`load_manifest()` 检测旧格式（字符串数组）时自动转换，下次保存时升 version。用户无需手动迁移。

### config.json：v2.0 字段扩展

```diff
 {
   "scan": { ... },
+  "default_scope": "global",
+  "link_strategy": "auto"
 }
```

---

## 8. 致谢

感谢 [youzaiAGI/agent-skills-hub](https://github.com/youzaiAGI/agent-skills-hub) 项目的开源，本项目从中借鉴了多个有价值的设计点。
