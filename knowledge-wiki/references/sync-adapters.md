# Sync Adapters

同步适配器负责知识库与远端之间的推送和拉取。通过适配器模式，核心逻辑不绑定特定平台。

## 适配器接口

```
push(kb_root, target_spec) -> sync_result
pull(kb_root, source_spec) -> sync_result
detect_conflicts(local, remote) -> conflict_list
resolve_conflict(strategy) -> resolved_content
```

---

## 内置适配器

### Git Adapter（默认）

基于 Git 远端仓库的同步。支持 GitHub、GitLab、Gitea 等任何 Git 托管平台。

#### push 流程

1. 检查本地是否有未提交的更改
2. `git add -A && git commit`（如有未提交更改）
3. `git push origin {branch}`
4. 如有冲突，`git pull --rebase origin {branch}` 后重试
5. 返回同步结果（推送的 commit 数、冲突数）

#### pull 流程

1. `git fetch origin {branch}`
2. 比较本地与远端的 diff
3. 如有远端更新：
   - `git stash`（如有本地未提交更改）
   - `git pull --rebase origin {branch}`
   - `git stash pop`（如之前 stash）
4. 识别远端新增/修改的 Wiki 页面
5. 如有冲突，调用冲突解决策略
6. 返回同步结果（拉取的页面数、冲突数）

#### detect_conflicts

```
git diff --name-only --diff-filter=U
```

#### 冲突解决策略

| 策略 | 说明 |
|------|------|
| `local-wins` | 保留本地版本 |
| `remote-wins` | 保留远端版本 |
| `merge` | 尝试自动合并（对 Markdown 文本效果好） |
| `manual` | 展示冲突，用户手动解决 |

#### 配置

在 `.schema/sync-targets.md` 中：

```markdown
## Git Sync Target

- adapter: git
- remote: origin
- branch: main
- conflict_strategy: merge
```

---

## 扩展适配器

### 语雀同步适配器（示例）

```markdown
## Yuque Sync Target

- adapter: yuque
- book_id: {book_id}
- namespace: {group}/{repo}
- direction: push-only
- conflict_strategy: local-wins
- mapping:
    wiki/entities/ → 语雀文档目录 "实体"
    wiki/concepts/ → 语雀文档目录 "概念"
    wiki/topics/ → 语雀文档目录 "主题"
    wiki/sources/ → 语雀文档目录 "源材料"
    wiki/code/ → 语雀文档目录 "代码知识"
```

push 流程：
1. 遍历 `wiki/` 下所有 `.md` 文件
2. 根据映射规则确定语雀目标目录
3. 检查语雀是否已有同名文档（通过 `skylark_search`）
4. 已有 → `skylark_doc_update`
5. 不存在 → `skylark_doc_create`
6. 更新 `.kb-state.json` 中的同步记录

### Skybase 同步适配器（示例）

```markdown
## Skybase Sync Target

- adapter: skybase
- kb_id: {kb_id}
- path: wiki/
- conflict_strategy: manual
```

push 流程：
1. `skybase auth whoami` 验证登录
2. 遍历 `wiki/` 下所有 `.md` 文件
3. `skybase note upload` 逐文件上传
4. 处理同名冲突（skip/overwrite/rename）

---

## 同步配置注册

在 `.schema/sync-targets.md` 中注册所有同步目标：

```markdown
# Sync Targets

## Primary
- adapter: git
- remote: origin
- branch: main

## Secondary (optional)
- adapter: yuque
- book_id: 12345
- direction: push-only
```

---

## sync 命令行为

### `kb-sync push`

1. 读取 `.schema/sync-targets.md` 获取同步目标列表
2. 对每个目标调用对应适配器的 `push()`
3. 报告每个目标的同步结果

### `kb-sync pull`

1. 读取 `.schema/sync-targets.md`
2. 对每个目标调用 `pull()`
3. 如有冲突，展示冲突列表并询问解决策略
4. 更新本地 Wiki 页面
5. 刷新 `wiki/index.md` 和 `wiki/AGENTS.md`

### `kb-sync status`

1. 对每个目标调用 `detect_conflicts()`
2. 展示本地与远端的差异摘要
3. 不执行任何同步操作