---
name: knowledge-wiki
version: 2.0.0
description: >
  统一知识库构建器，融合 LLM Wiki 方法论与代码仓库深度分析。支持多源摄入（网页、语雀、飞书、PDF、
  本地文件、GitHub 仓库、YouTube、arXiv、RSS）、代码知识提取（架构/接口/模型/流程）、知识图谱构建、
  语义检索（qmd）、两级健康检查（自动修复+语义报告）、探索发现与学习路径、SHA-256 增量更新、
  查询沉淀（每次查询丰富知识库）、Git 云同步。业务知识与代码知识通过 wikilink 双向关联，
  形成可复合增长的结构化知识体系。
  关键词：知识库、wiki、knowledge base、codewiki、ingest、摄入、代码分析、知识图谱、知识管理。
description_zh: >
  基于 Karpathy LLM Wiki 方法论的统一知识库构建器 v2。业务知识与代码知识一体两面，
  查询结果沉淀为合成页持续丰富知识库，SHA-256 变更检测驱动精准增量更新，
  知识图谱可视化关系网络，两级 lint 自动修复结构问题。
---

# Knowledge Wiki — 统一知识库构建器

基于 **[Karpathy LLM Wiki 方法论](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)**，构建和维护持久化、可复合增长的结构化知识库。业务知识与代码知识共存于同一 Wiki，通过 wikilink 双向追溯。

## 触发条件

Trigger this skill when:
- `/knowledge-wiki init` — 创建新知识库
- `/knowledge-wiki ingest` — 摄入源材料
- `/knowledge-wiki query` — 查询知识库
- `/knowledge-wiki lint` — 健康检查
- `/knowledge-wiki explore` — 探索知识空白
- `/knowledge-wiki update` — 增量更新
- `/knowledge-wiki sync` — 云端同步
- Keywords: 知识库, knowledge base, KB, wiki, ingest, 摄入, codewiki, 代码知识库, 知识管理

Do NOT trigger for:
- 单次网页搜索（直接用 fetch_content）
- 简单文件读取（直接用 Read）
- 纯代码分析不涉及知识结构化（直接用代码分析工具）

---

## 一、核心理念

- **编译而非检索**：摄入是一次性编译，将原始材料转化为结构化 Wiki 页面。知识沉淀后跨会话持续积累，不再每次从零推导
- **查询即丰富**：每次查询的结果可沉淀为合成页（synthesis），触发级联更新——创建缺失的实体/概念页、更新交叉引用、重建图谱。查询不是消耗，而是知识增长
- **持久化与复合增长**：每次摄入不仅新增页面，还更新已有页面的交叉引用和综合分析
- **业务与代码一体**：业务概念页 `[[结算周期]]` 直接链接到代码实现页 `[[SettlementService]]`，反之亦然
- **适配器模式**：源摄入、代码仓库、云同步均通过适配器扩展，核心逻辑不绑定特定平台
- **三层分离**：Raw（不可变原始材料）、Wiki（LLM 维护的结构化知识）、Schema（用户+LLM 共同演进的配置）
- **SHA-256 变更检测**：基于内容哈希而非时间戳检测变更，精准识别真正修改的源文件，避免无谓重摄入
- **知识图谱**：三层边类型（EXTRACTED/INFERRED/AMBIGUOUS），从 wikilink 提取确定关系，LLM 推断隐式关系，可视化知识网络

---

## 二、目录结构

```
{kb-root}/
  README.md                             # 用户说明书（知识库定位、重点关注方向、偏好）
  raw/                                  # Layer 1: 原始源（不可变）
    business/                           # 业务源文档
      assets/                           # 下载的图片/附件
      {adapter}/{source-name}.md        # 按适配器分目录：yuque/, feishu/, web/, local/
    code/                               # 代码仓库引用（不放代码本身）
      {repo-name}/
        repo-meta.json                  # 仓库元数据（URL, branch, last-analyzed commit）

  wiki/                                 # Layer 2: Wiki（LLM 维护）
    index.md                            # 🔑 统一导航枢纽
    overview.md                         # 全局综合（业务+代码）
    AGENTS.md                           # LLM 快速导航文件（精简索引 + 检索策略）

    # ─── 业务知识域 ───
    entities/                           # 实体：组织、系统、API、渠道
    concepts/                           # 概念：模式、原则、协议
    topics/                             # 主题：领域分区（hub 页）
    sources/                            # 每源摘要页
    analyses/                           # 查询归档、对比分析
    maps/                               # 关系图谱（Mermaid/文字描述）

    # ─── 代码知识域 ───
    code/
      architecture/                     # 架构文档（每系统一页）
        {system-name}.md
      modules/                          # 模块索引
        _index.md                       # 精简索引（名称+职责+路径）
      interfaces/                       # 接口详细索引
        _index.md
        {group}.md                      # ≥10 接口时按模块分组
      data-models/                      # 数据模型索引
        _index.md
        {group}.md                      # ≥10 模型时分组
      flows/                            # 核心业务流程
        _index.md
        {flow-name}.md
      contracts/                        # API 合约 & 配置变更
      conventions.md                    # 编码约定
      dependencies.md                   # 外部依赖图
      glossary.md                       # 技术术语表

    # ─── 跨域 ───
    changelog/                          # 统一变更追踪

  log.md                                # 时间线活动日志
  .schema/                              # Layer 3: Schema
    CLAUDE.md                           # Claude Code 操作指令
    AGENTS.md                           # OpenAI Codex 操作指令
    conventions.md                      # Wiki 约定
    source-adapters.md                  # 已注册的源适配器配置
    code-repos.md                       # 关联的代码仓库
    sync-targets.md                     # 云同步目标配置
  .kb-state.json                        # KB 全局状态（含源文件 SHA-256 哈希）
  .codewiki-meta.json                   # 代码分析元数据（hash、版本、增量追踪）
  graph/                                # 知识图谱
    graph.json                          # 节点+边数据（EXTRACTED/INFERRED/AMBIGUOUS）
    graph.html                          # 可视化 HTML（D3/force-directed）
  .kbignore                             # 摄入/分析范围排除规则
  .qmd/                                 # qmd 搜索索引
  .gitignore
```

---

## 三、依赖

| 依赖 | 用途 | 必需 |
|------|------|------|
| git | 版本管理、增量检测、云同步 | 推荐 |
| qmd CLI / MCP | 向量嵌入、语义搜索 | 推荐（大型 KB） |
| 源适配器 MCP（按需） | 语雀: skylark_*, 飞书: feishu_* | 条件 |
| `pdf` skill | 解析 PDF 格式源文档 | 条件 |
| `docx` skill | 解析 DOCX 格式源文档 | 条件 |

---

## 四、命令总览

| 命令 | 用途 | 详情 |
|------|------|------|
| `init` | 初始化新知识库 | 创建目录结构、Schema 文件、`.kbignore`、Git 仓库 |
| `ingest` | 摄入源材料 | SHA-256 去重 + 适配器路由 + 提炼 Wiki 页面 |
| `query` | 查询知识库 | 多策略检索，综合回答，**结果可沉淀为合成页** |
| `lint` | 健康检查 | **两级**：结构问题自动修复，语义问题仅报告 |
| `explore` | 探索发现 | 识别知识空白 + **生成学习路径** |
| `update` | 增量更新 | SHA-256 变更检测，定向更新受影响页面 |
| `graph` | 构建知识图谱 | 提取 wikilink + LLM 推断隐式关系，生成可视化 |
| `sync` | 云端同步 | 推送/拉取，冲突检测与合并 |

---

## 五、执行流程

### Phase 1 — 初始化 (kb-init)

**目标**：创建知识库，建立完整目录结构和 Schema。

1. 使用 `AskUserQuestion` 收集：KB 名称、根目录路径、Git 仓库 URL（可选）、领域描述、关联代码仓库（可选）
2. 创建目录结构（如上所示）
3. 生成初始文件：`README.md`、`.schema/CLAUDE.md`、`.schema/AGENTS.md`、`.schema/conventions.md`、`.schema/source-adapters.md`、`.schema/code-repos.md`、`.schema/sync-targets.md`、`wiki/index.md`、`wiki/overview.md`、`wiki/AGENTS.md`、`log.md`、`.kb-state.json`、`.codewiki-meta.json`、`.gitignore`、`.kbignore`
4. **用户编写 README.md 说明书**：引导用户填写知识库定位、重点关注方向、偏好（这是 AI 理解知识库上下文的首要入口）
5. Git 初始化（clone 或 init）
6. qmd 注册（如可用）
7. 初始 commit

详细初始化脚本见 `scripts/kb_init.py`。

#### README.md — 知识库说明书

`README.md` 是知识库的**首要入口文件**，由用户编写，AI 在每次操作时首先读取。它回答"这个知识库是什么、我重点关注什么、我希望 AI 怎么帮我"。

模板结构：

```markdown
# {kb-name}

## 这是什么？
> 一段话描述这个知识库的主题和目标。
> 例如：一个关于【支付系统架构】的个人知识库，记录支付渠道、结算流程、风控策略的设计与实现。

## 文件夹规则
- `raw/`：原始素材，永远不要修改或删除
- `wiki/`：AI 整理的维基，完全由 AI 维护
- `graph/`：知识图谱数据，由 AI 生成
- `.schema/`：配置文件，用户和 AI 共同维护

## 维基整理规则
- 每个主题一个 .md 文件，放在对应目录（entities/、concepts/、topics/）
- 开头写 YAML frontmatter，包含 title、type、tags、updated
- 用 [[topic-name]] 链接相关主题
- 维护 wiki/index.md 索引
- 添加新素材时，更新相关维基页面

## 重点关注方向
1. 【方向1，如：支付渠道接入模式】
2. 【方向2，如：结算周期与对账机制】
3. 【方向3，如：风控策略与限额体系】

## 源保留偏好
- 重要业务文档：local 保留（完整保存到 raw/）
- 公开网页/视频：link 保留（仅保存元数据和链接）

## 关联代码仓库
- 【仓库1 URL】— 简要说明
- 【仓库2 URL】— 简要说明

## 备注
> 任何其他你想让 AI 知道的信息。
```

**关键原则**：
- README.md 由**用户**编写和维护，AI 不主动修改
- AI 在每次查询、摄入、lint 操作前**先读 README.md**，理解用户上下文
- README.md 的内容会影响 AI 的摄入优先级、查询侧重、explore 建议（特别是"重点关注方向"）
- 用户可随时编辑 README.md 来调整知识库的方向

### Phase 2 — 摄入 (kb-ingest)

**目标**：接受源材料，提炼为结构化 Wiki 页面，更新索引和日志。

#### 源类型路由

通过适配器模式处理不同源类型。内置适配器和扩展方式详见 `references/source-adapters.md`。

| 源类型 | 适配器 | 检测规则 |
|--------|--------|---------|
| Web 文章 | `web` | `http(s)://` 非已知笔记平台域名 |
| 语雀文章 | `yuque` | `yuque.com/` 或 `yuque.antfin.com/` |
| 语雀知识库 | `yuque` | 语雀 repo URL 或用户指定为「整个知识库」|
| 飞书文档 | `feishu` | `feishu.cn/` 或 `larksuite.com/` |
| YouTube 视频 | `youtube` | `youtube.com/watch` 或 `youtu.be/` |
| arXiv 论文 | `arxiv` | `arxiv.org/abs/` 或 `arxiv.org/pdf/` |
| RSS 订阅 | `rss` | RSS/Atom feed URL |
| Jupyter Notebook | `jupyter` | 文件路径 `.ipynb` |
| PPT 演示 | `pptx` | 文件路径 `.pptx` |
| CSV 数据 | `csv` | 文件路径 `.csv` |
| 本地 Markdown | `local-markdown` | 文件路径 `.md` |
| 本地 PDF | `local-pdf` | 文件路径 `.pdf` |
| 本地 DOCX | `local-docx` | 文件路径 `.docx` |
| GitHub 仓库 | `github` | `github.com/` URL 或用户指定「代码仓库」|
| 其他 Git 仓库 | `git` | `.git` 结尾 URL |

新适配器注册：在 `.schema/source-adapters.md` 中添加适配器配置即可扩展。

#### 摄入核心流程

1. **路由**：根据源类型选择适配器
2. **去重检查**：计算源内容的 SHA-256 哈希，与 `.kb-state.json` 中的 `source_registry` 比对：
   - 哈希相同 → 跳过，告知用户"源未变更"
   - 哈希不同 → 标记为 `updated`，重新摄入并更新相关 Wiki 页面
   - 新源 → 标记为 `new`，完整摄入
3. **获取**：适配器 fetch 源内容，根据保留策略保存：
   - `local` 保留：完整内容保存到 `raw/{adapter}/`
   - `link` 保留：仅保存元数据和原始链接到 `raw/{adapter}/`（适配器自动选择默认值，用户可覆盖）
4. **叙事分析**（Narrative Analysis）：提取核心论点、演化脉络、约束风险、具体示例
4. **提炼 Wiki 页面**：
   - 源摘要页 → `wiki/sources/source-{name}.md`
   - 实体页 → `wiki/entities/{name}.md`（新建或追加）
   - 概念页 → `wiki/concepts/{name}.md`（新建或追加）
   - 主题页 → `wiki/topics/{name}.md`（按需）
   - 对比分析页 → `wiki/analyses/{topic}.md`（源文档显式对比时）
5. **完整性检查**（Completeness Check）：约束覆盖、示例覆盖、叙事保留、风险分配、阈值值
6. **更新导航**：`wiki/index.md`、`wiki/AGENTS.md`、`log.md`、`wiki/overview.md`
7. **质量验证**（Quality Gate）：详见 `references/quality-gates.md`
8. **qmd 嵌入**（如可用）
9. **Git commit**

页面模板详见 `references/wiki-page-templates.md`。

#### 代码仓库摄入

代码仓库摄入走独立的 6 阶段流水线，输出到 `wiki/code/` 目录。详见 `references/code-analysis-pipeline.md`。

关键差异：代码分析产物是 **Wiki 一等公民**，拥有 frontmatter、wikilinks、tags，可被业务页面引用，也可反向引用业务页面。

#### 批量摄入

当源为整个知识库（语雀/飞书）时：
1. 适配器 list 所有文档
2. 展示清单，用户确认范围
3. 按目录分组，每组 3-5 篇并发生成（SubAgent）
4. 每 5 篇展示进度
5. 全部完成后统一 qmd embed 和 git commit

### Phase 3 — 查询 (kb-query)

1. **读取 `README.md`**（用户说明书，理解知识库上下文和重点关注方向）
2. 读取 `wiki/AGENTS.md`（精简导航）和 `wiki/index.md`（完整索引）
2. 按 KB 规模选择检索策略：

| KB 规模 | 页面数 | 策略 |
|---------|--------|------|
| 小型 | < 50 | AGENTS.md 直接导航 |
| 中型 | 50-200 | AGENTS.md + qmd keyword 辅助 |
| 大型 | > 200 | qmd 语义搜索优先 |
| 复杂查询 | 任意 | qmd hybrid 检索 + 重排序 |

3. 读取相关页面，综合回答（含 wikilink 引用、置信度、知识空白）
4. 复杂分析结果可归档为 `wiki/analyses/` 页面

#### 查询沉淀（Synthesis-as-Enrichment）

当用户选择将查询结果归档时，触发**级联更新**——这不仅是保存一个页面，而是让知识库从每次查询中增长：

1. 创建合成页 → `wiki/analyses/{topic}.md`
2. 扫描合成页中所有 `[[wikilinks]]`，对每个链接：
   - 目标页面已存在 → 更新其交叉引用章节
   - 目标页面不存在 → 创建占位实体/概念页（标记 `status: draft`）
3. 更新 `wiki/index.md`（Analyses 分区 + 新创建的占位页）
4. 更新 `wiki/overview.md`（如合成页涉及全局知识）
5. 重建知识图谱（更新 `graph/graph.json`）
6. 追加到 `log.md`

这意味着**每次深度查询都是一次微摄入**，知识库会随使用而不断丰富。

### Phase 4 — 健康检查 (kb-lint)

两级检查策略：**结构问题自动修复，语义问题仅报告**。

#### 第一阶段：自动修复（无需确认）

| 检查类别 | 说明 | 动作 |
|----------|------|------|
| 断链修复 | `[[wikilink]]` 指向不存在的页面 | 自动创建占位页面（`status: draft`） |
| 孤岛修复 | 无入站 wikilink 的页面（maps/ 除外） | 在相关页面的关联章节添加指向孤立页的 wikilink |
| Frontmatter 补全 | 页面缺少必填 YAML 字段 | 自动补全 `title`、`type`、`sources`、`updated` |
| 索引遗漏 | 页面存在但未在 index.md 中列出 | 自动添加到 index.md 对应分区 |
| 源去重 | 同一源被摄入多次 | 保留最新版本，移除重复的源摘要页 |

#### 第二阶段：语义报告（需人工判断）

| 检查类别 | 说明 | 严重级别 |
|----------|------|----------|
| 矛盾检测 | 不同页面对同一事实的矛盾描述 | ERROR |
| 过时信息 | 新源更新后旧摘要未同步 | WARNING |
| 概念缺页 | 被提及 >=3 次但无独立页面的概念/实体 | INFO |
| 缺失交叉引用 | 相关页面间缺少 wikilink | INFO |
| 数据空白 | 知识库无法回答的重要问题 | INFO |
| 源覆盖度 | raw/ 中已有但未摄入 wiki 的源 | INFO |
| 已删除源 | raw/ 中已丢失但 wiki/sources/ 仍有对应页面 | WARNING |
| 代码页覆盖度 | 已注册仓库但未生成 wiki/code/ 页面 | WARNING |
| 代码同步度 | 代码页与仓库最新 commit 的偏差 | INFO |
| 业务-代码脱节 | 代码页无业务链接或业务页无代码链接 | WARNING |
| 图谱边缺失 | 高度相关但未建立 wikilink 的页面对 | INFO |

#### 源不可达处理

**重要原则：禁止删除源文件和对应的 wiki 页面。** 即使远端源不可达，本地保留的内容仍是知识库的不可变基础。

当检测到 link 保留方式的源不可达时：
1. 在 `.kb-state.json` 中标记源为 `unreachable`
2. 在 lint 报告中列出不可达源（WARNING 级别）
3. 保留所有 wiki 页面和源摘要页不变
4. 提示用户可选择：**重新获取** / **升级为 local 保留** / **暂时忽略**

对于 local 保留方式的源，不存在不可达问题——本地文件始终可用。

#### Lint 输出

```markdown
# KB Lint Report - {kb-name}
> Date: {date} | Pages scanned: {count} | Auto-fixed: {n} | Issues reported: {m}

## Auto-fixed
- ✅ Created placeholder: [[{Missing Page}]] (broken link from [[{Source}]])
- ✅ Added inbound link: [[{Orphan Page}]] ← [[{Related Page}]]
- ✅ Completed frontmatter: {page}.md (added: type, updated)

## Issues (require review)
- 🔴 **Contradiction**: Settlement cycle described as T+1 in [[source-a]] but T+2 in [[source-b]]
- 🟡 **Stale claim**: [[channel-x]] references API v1, but [[source-new]] confirms v2
- 🟡 **Deleted source**: raw/business/yuque/old-doc.md missing, wiki/sources/source-old-doc.md is orphaned
- 🟢 **Missing page**: "HMAC Authentication" mentioned 5 times but has no page
```

### Phase 5 — 探索发现 (kb-explore)

1. 阅读 `wiki/overview.md`、`wiki/index.md`、`log.md`（最近 30 条）
2. 盘点 raw/ 素材覆盖范围
3. 分析知识版图：
   - **充分覆盖**：多页关联、内容深入
   - **薄弱覆盖**：单页孤立、内容浅显
   - **空白主题**：被提及但无独立页面
   - **孤立页面**：无入链或出链
   - **矛盾**：存在冲突的观点
   - **代码-业务脱节**：代码页无业务概念链接，或业务概念无代码实现链接
4. 生成 3-5 个具体研究方向建议
5. **学习路径生成**：基于知识版图分析，为空白或薄弱区域生成 guided learning tour：
   ```
   ## Learning Tour: {主题}
   **目标**：掌握 {主题} 的核心概念和实现
   **难度**：beginner | intermediate | advanced
   **预计时间**：{n} 页阅读

   ### 路径
   1. [[concept-a]] — 基础概念（先读）
   2. [[entity-x]] — 关键实体
   3. [[code/modules/y]] — 代码实现
   4. [[flow-z]] — 端到端流程

   ### 延伸阅读
   - [[related-topic]] — 深入理解
   ```
6. 追加到 `log.md`

### Phase 6 — 增量更新 (kb-update)

统一调度所有源类型的变更检测，基于 SHA-256 内容哈希而非时间戳。支持子命令：

| 子命令 | 说明 |
|--------|------|
| `update source` | 检测业务源变更（SHA-256 哈希比对） |
| `update code` | 检测代码仓库变更（git log / adapter diff） |
| `update index` | 手动编辑后刷新 AGENTS.md 和 index.md |
| `update graph` | 重建知识图谱（提取 wikilink + LLM 推断） |
| `update all` | 全量检测所有源 + 重建图谱 |

#### SHA-256 变更检测

所有源文件在摄入时计算 SHA-256 哈希，存入 `.kb-state.json` 的 `source_registry`：

```json
{
  "source_id": "yuque/doc-12345",
  "adapter": "yuque",
  "sha256": "a1b2c3d4...",
  "ingested_at": "2025-01-15T10:30:00Z",
  "wiki_pages": ["entities/payment-channel.md", "concepts/settlement.md"],
  "preservation": "local"
}
```

更新流程：
1. 重新获取源内容，计算新 SHA-256
2. 与 `.kb-state.json` 中记录的哈希比对
3. **哈希相同** → 跳过（源未变更）
4. **哈希不同** → 标记为 `updated`，重新摄入并更新关联 Wiki 页面
5. **新源** → 标记为 `new`，完整摄入

优势：避免时间戳不可靠（服务器时钟偏移、缓存问题），精准识别真正修改的源。

#### 代码更新策略

代码更新采用**保鲜机制**（借鉴 wiki-document-refresher）：
1. 适配器 `detect_changes()` 返回变更文件列表
2. 确定影响范围（级联规则：接口变更→更新接口页+关联模块页+关联流程页）
3. 定向更新受影响的 Wiki 页面（非全量重跑）
4. 代码变更可能影响业务页：如接口签名变更→更新引用该接口的实体页
5. 更新 `.codewiki-meta.json` 中的文件 hash 和 commit 记录

#### 业务源更新策略

1. 适配器 `detect_changes()` 返回变更文档列表
2. 重新摄入变更文档
3. 对比旧版摘要，更新相关 Wiki 页面
4. 重要变更记录到 `wiki/changelog/`

#### 源文件保留策略

**重要原则：禁止删除源文件。** raw/ 中的原始材料是知识库不可变基础，即使源文档在远端被删除，本地保留的 raw 文件仍应保留。

保留方式根据源的重要性选择：

| 保留方式 | 说明 | 适用场景 |
|----------|------|----------|
| `local` | 原始文件完整保存到 `raw/` | 核心业务文档、唯一来源、可能下线的内容 |
| `link` | 仅保留元数据和原始链接 | 公开网页、可随时重新获取的内容、大文件 |

在 `.kb-state.json` 的 `source_registry` 中通过 `preservation` 字段标记。用户可在摄入时指定，或由适配器根据源类型自动选择默认值。

当检测到远端源不可达时：
- **local 保留**：无需任何操作，本地文件仍然可用
- **link 保留**：标记源为 `unreachable`，提示用户，但不删除 wiki 页面和源摘要页

### Phase 7 — 云同步 (kb-sync)

通过适配器模式支持多种同步目标。详见 `references/sync-adapters.md`。

| 子命令 | 说明 |
|--------|------|
| `sync push` | 推送本地 Wiki 到远端 |
| `sync pull` | 从远端拉取更新到本地 |
| `sync status` | 检查本地与远端的差异 |

内置适配器：
- **git**：推送到 GitHub/GitLab 远端仓库（默认）
- 扩展适配器注册在 `.schema/sync-targets.md`

### Phase 8 — 知识图谱 (kb-graph)

构建知识图谱，可视化页面间的关系网络。详见 `references/knowledge-graph.md`。

1. **提取 EXTRACTED 边**：扫描所有 wiki 页面中的 `[[wikilinks]]`，提取确定性的页面引用关系
2. **推断 INFERRED 边**：LLM 分析页面内容，推断隐式语义关系（置信度 ≥ 0.7）
3. **标记 AMBIGUOUS 边**：LLM 置信度 < 0.7 的弱关系，标记为待确认
4. **生成图谱数据**：输出 `graph/graph.json`（节点 + 三类边）
5. **生成可视化**：输出 `graph/graph.html`（D3 force-directed 布局）
6. **更新导航**：在 `wiki/index.md` 和 `wiki/AGENTS.md` 中添加图谱链接

#### 边类型

| 边类型 | 来源 | 置信度 | 示例 |
|--------|------|--------|------|
| EXTRACTED | wikilink 提取 | 1.0 | `[[payment-channel]]` → `[[settlement]]` |
| INFERRED | LLM 推断 | ≥ 0.7 | "支付渠道依赖结算周期"（无显式 wikilink） |
| AMBIGUOUS | LLM 推断 | < 0.7 | "可能相关"（需人工确认） |

#### 图谱数据格式

```json
{
  "nodes": [
    { "id": "payment-channel", "label": "支付渠道", "type": "entity", "domain": "business" },
    { "id": "settlement-service", "label": "SettlementService", "type": "module", "domain": "code" }
  ],
  "edges": [
    { "source": "payment-channel", "target": "settlement", "type": "EXTRACTED", "confidence": 1.0, "label": "depends_on" },
    { "source": "payment-channel", "target": "settlement-service", "type": "INFERRED", "confidence": 0.85, "label": "implemented_by" }
  ],
  "metadata": { "generated_at": "...", "total_nodes": 42, "total_edges": 78 }
}
```

---

## .kbignore 规范

`.kbignore` 控制摄入和分析的范围排除规则，语法兼容 `.gitignore`：

```gitignore
# 排除特定目录
raw/business/yuque/drafts/
wiki/code/**/test-*

# 排除特定文件模式
*.tmp
*.bak
.DS_Store

# 排除特定适配器的源
raw/business/web/archive/

# 排除代码仓库中的路径
code:src/generated/**
code:**/*.pb.go

# 排除大型二进制文件
*.pdf
*.pptx
```

**规则**：
- 每行一条规则，`#` 开头为注释
- 支持 glob 模式（`*`、`**`、`?`）
- `code:` 前缀表示代码仓库路径排除规则（而非 wiki/raw 路径）
- 否定模式用 `!` 前缀（如 `!important.pdf` 重新包含）
- 适配器在 `fetch` 和 `list` 时检查 `.kbignore`，跳过匹配的文件

---

## 六、适配器体系

### 源适配器接口

每个源适配器实现以下接口：

```
detect(source_spec) -> boolean          # 能否处理此源
fetch(source_spec) -> raw_content       # 获取原始内容
list(source_spec) -> [source_items]     # 列出所有项（批量源）
detect_changes(spec, last_state) -> []  # 检测变更
to_markdown(raw_content) -> markdown    # 转换为 Markdown
```

内置适配器规格详见 `references/source-adapters.md`。

在 `.schema/source-adapters.md` 中注册自定义适配器：

```markdown
## 自定义适配器：confluence

- detect: URL 包含 `confluence.` 或 `atlassian.net/wiki/`
- fetch: 使用 Confluence REST API（需配置 token）
- to_markdown: 将 Confluence storage format 转 Markdown
- config:
    base_url: https://confluence.example.com
    token_env: CONFLUENCE_TOKEN
```

### 代码仓库适配器接口

```
detect(repo_spec) -> boolean
clone_or_pull(repo_spec) -> local_path
detect_changes(repo_spec, last_state) -> change_set
get_file_content(repo_spec, file_path) -> content
```

内置：`github`（git clone + git log + git diff）。扩展：在 `.schema/code-repos.md` 中注册。

### 同步适配器接口

```
push(kb_root, target_spec) -> sync_result
pull(kb_root, source_spec) -> sync_result
detect_conflicts(local, remote) -> conflict_list
```

内置：`git`（git push/pull）。扩展：在 `.schema/sync-targets.md` 中注册。

---

## 七、跨域链接

业务知识与代码知识的双向链接是本技能的核心差异化：

**业务→代码**：实体页和概念页的 `## Code Implementation` 章节
```markdown
## Code Implementation
- [[code/modules/settlement-service|SettlementService]] — 结算周期核心实现
- [[code/interfaces/SettlementFacade|SettlementFacade]] — 对外结算接口
```

**代码→业务**：代码页的相关业务章节
```markdown
## Business Context
- [[settlement-cycle|结算周期]] — 本模块实现的业务概念
- [[payment-channel|支付渠道]] — 上游调用方
```

**自动链接建议**：在 `lint` 和 `explore` 阶段，检测代码页与业务页之间的缺失链接，生成建议。

---

## 八、AGENTS.md 导航文件

`wiki/AGENTS.md` 是为 LLM 优化的精简导航文件（借鉴 Evobase），提供：

1. **知识库元信息**：名称、领域、页面统计
2. **目录结构速览**：各目录的职责和页面数
3. **检索策略**：根据问题类型推荐检索路径
4. **热点页面**：高频访问的 Top 10 页面

LLM 查询时**先读 AGENTS.md**，避免遍历整个知识库。

---

## 九、Obsidian 兼容性

YAML frontmatter、wikilinks、标签体系、Dataview 兼容、Graph View 优化、Marp 演示支持。
详见 `references/obsidian-conventions.md`。

---

## 十、qmd 集成

语义搜索、向量嵌入、混合检索。详见 `references/qmd-integration.md`。

降级策略：qmd 不可用时退化为 AGENTS.md 导航 + grep 全文搜索。

---

## 输入

| 输入项 | 来源 | 必需 |
|--------|------|------|
| 操作类型 | 用户指令 | 是 |
| KB 名称 / 路径 | 用户提供（init 时）或从 .kb-state.json 读取 | 是 |
| 源 URL / 文件路径 | 用户提供（ingest 时） | ingest 时必需 |
| 查询问题 | 用户提供（query 时） | query 时必需 |
| 同步目标 | 配置文件或用户指定 | sync 时 |

## 输出

| 输出 | 路径 | 说明 |
|------|------|------|
| KB 完整目录 | `{kb-root}/` | 三层架构全部文件 |
| 用户说明书 | `{kb-root}/README.md` | 用户编写的知识库定位、重点关注方向和偏好 |
| Wiki 页面 | `{kb-root}/wiki/**/*.md` | 业务+代码页面 |
| 导航文件 | `{kb-root}/wiki/AGENTS.md` | LLM 精简导航 |
| 内容索引 | `{kb-root}/wiki/index.md` | 完整页面链接 |
| 活动日志 | `{kb-root}/log.md` | 时间线操作记录 |
| Schema 文件 | `{kb-root}/.schema/*` | 配置和约定 |
| KB 状态 | `{kb-root}/.kb-state.json` | 增量更新状态 |
| 代码分析元数据 | `{kb-root}/.codewiki-meta.json` | 代码增量追踪 |
| qmd 索引 | `{kb-root}/.qmd/` | 语义搜索索引 |

---

## 错误处理

| 错误场景 | 处理策略 |
|----------|----------|
| 源适配器不可用 | 提示缺少的 MCP 或工具，跳过该源继续 |
| qmd 未安装 | 降级为 AGENTS.md + grep 搜索 |
| Git 操作失败 | 提示错误详情，尝试不使用 git 继续 |
| 超大源文档 | 分段处理，提示用户可能需要较长时间 |
| 信息矛盾 | 展示矛盾，用户选择保留哪个版本 |
| 代码仓库 clone 失败 | 提示检查权限，标记代码集成为不可用 |
| 批量摄入中断 | 保存进度到 `.kb-state.json`，支持断点恢复 |
| 同步冲突 | 展示冲突详情，提供合并/覆盖/跳过选项 |
| 源不可达 | 标记 `unreachable`，保留 wiki 页面，提示用户选择重新获取或升级保留方式 |
| 知识图谱推断失败 | 保留 EXTRACTED 边，跳过 INFERRED/AMBIGUOUS 边，在 graph.json 中标注 |
| .kbignore 规则冲突 | 否定模式（`!`）优先于排除模式，与 .gitignore 行为一致 |