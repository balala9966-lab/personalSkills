# Code Analysis Pipeline

代码仓库摄入走独立的 6 阶段流水线，输出到 `wiki/code/` 目录。所有代码分析产物都是 **Wiki 一等公民**，拥有 YAML frontmatter、wikilinks、tags。

## 运行模式

| 触发方式 | 模式 |
|----------|------|
| 首次摄入代码仓库 | 全量生成 |
| `update code` | 增量更新（仅处理变更文件） |
| `update code --module <name>` | 单模块分析 |

---

## 阶段流水线

| Phase | 名称 | 输出 | 质量关卡 |
|-------|------|------|----------|
| 0 | 远程缓存检查 | wiki/code/ (从远端拉取) 或跳过 | — |
| 1 | 项目探测 | 项目画像 JSON | 语言/框架/入口已识别 |
| 2 | 架构分析 | architecture/{system}.md + conventions.md | 架构描述准确 |
| 3 | 模块索引 | modules/_index.md | 所有模块已索引 |
| 4 | 接口与模型 | interfaces/ + data-models/ 详细索引 | 接口签名准确 |
| 5 | 流程与关系 | flows/*.md + dependencies.md + glossary.md | 流程覆盖核心场景 |
| 6 | 终审 | 更新 index.md + AGENTS.md + .codewiki-meta.json | 完整性终检通过（强卡点）|

---

## Phase 0: 远程缓存检查

全量/增量模式默认执行，`--force` 跳过。

检查代码仓库是否有预生成的 codewiki 缓存（如远端 `.zm_sdd/codewiki/` 或 Git LFS 存储）。

**命中** → 复制到 `wiki/code/`，调整 frontmatter 格式，结束
**未命中** → 继续 Phase 1-6

---

## Phase 1: 项目探测

1. 读取 `README.md`（如存在）
2. 生成目录树（深度 3）
3. 识别关键配置文件（`pom.xml`、`package.json`、`go.mod`、`Cargo.toml` 等）
4. 识别主语言和框架
5. 识别入口点（`main` 函数、`Application` 类、路由配置等）
6. 输出项目画像 JSON：

```json
{
  "language": "Java",
  "framework": "Spring Boot",
  "build_tool": "Maven",
  "entry_points": ["src/main/java/com/example/Application.java"],
  "modules": ["user-service", "order-service", "payment-gateway"],
  "key_configs": ["pom.xml", "application.yml"]
}
```

---

## Phase 2: 架构分析

**目标**：生成系统架构文档和编码约定文档。

**并行触发条件**：模块 >= 3 或源文件 >= 100 时，架构分析和约定分析并行执行。

### 架构分析输出 → `wiki/code/architecture/{system-name}.md`

使用 Architecture Page 模板（见 `wiki-page-templates.md`），包含：
- System Overview
- Components 表
- Data Flow 图
- Integration Points
- Dependencies
- **Business Context** 章节（链接到业务 Wiki 页面）

### 编码约定输出 → `wiki/code/conventions.md`

- 代码风格约定
- 命名规范
- 分层规则
- 错误处理模式
- 日志规范

---

## Phase 3: 模块索引

**目标**：生成精简模块索引，不做单模块详细文件。

输出 → `wiki/code/modules/_index.md`

```markdown
| 模块 | 职责 | 路径 | 关键接口 | 业务概念 |
|------|------|------|----------|----------|
| user-service | 用户管理 | src/user/ | UserService, UserController | [[用户]] |
| order-service | 订单处理 | src/order/ | OrderService | [[订单]], [[结算周期]] |
```

**渐进式披露**：AI 通过索引定位入口路径后，自行 Read 源码获取详情。

---

## Phase 4: 接口与模型

**始终并行**：接口提取和模型提取同时执行。

### 接口索引 → `wiki/code/interfaces/`

- `_index.md`：导航索引
- `{group}.md`：当接口 >= 10 时按模块分组

每个接口条目包含：
- 方法签名
- 请求/响应类型
- 业务含义（链接到业务 Wiki 页面）
- 调用方和被调用方

### 数据模型索引 → `wiki/code/data-models/`

- `_index.md`：导航索引
- `{group}.md`：当模型 >= 10 时按模块分组

每个模型条目包含：
- 字段列表
- 表名/集合名
- 业务含义
- 关联模型

---

## Phase 5: 流程与关系

**并行触发条件**：流程 >= 2 时，多个流程分析并行执行。

### 核心业务流程 → `wiki/code/flows/`

- `_index.md`：流程清单
- `{flow-name}.md`：单流程详情

每个流程包含：
- 触发条件
- 参与模块/接口
- 数据流转
- 业务概念链接

### 外部依赖 → `wiki/code/dependencies.md`

### 术语表 → `wiki/code/glossary.md`

---

## Phase 6: 终审

**强卡点**：完整性终检不通过时，不允许结束，必须回退补全。

检查项：
1. **模块覆盖**：所有识别的模块是否在 `_index.md` 中有条目？
2. **接口覆盖**：所有 public 接口是否在 `interfaces/` 中有记录？
3. **模型覆盖**：所有核心数据模型是否在 `data-models/` 中有记录？
4. **业务链接**：每个代码页是否至少有一个到业务 Wiki 页面的 wikilink？
5. **Frontmatter 一致性**：所有页面是否包含必填 YAML 字段？
6. **索引更新**：`wiki/index.md` 和 `wiki/AGENTS.md` 是否已更新？

通过后：
- 更新 `wiki/index.md` 的代码知识域分区
- 更新 `wiki/AGENTS.md` 的检索策略
- 更新 `.codewiki-meta.json`（文件 hash、版本号、commit SHA）

---

## 增量更新模式

1. 读取 `.codewiki-meta.json` 获取文件 hash 和映射
2. 代码仓库适配器 `detect_changes()` 返回变更文件列表
3. 确定影响范围（级联规则）：

| 变更类型 | 影响范围 |
|----------|----------|
| 接口签名变更 | 该接口页 + 关联模块页 + 关联流程页 + 引用该接口的业务页 |
| 数据模型变更 | 该模型页 + 关联接口页 + 引用该模型的业务页 |
| 模块内部变更 | 该模块索引条目 + 受影响的流程页 |
| 架构级变更 | architecture/ 全部重跑 + 所有模块索引 |

4. 仅重跑受影响的阶段
5. Phase 6 终审全量运行

---

## 单模块模式

跳过 Phase 1-2，仅分析指定模块及其关联接口/流程。

---

## SubAgent 调度

| Agent | 阶段 | 触发条件 |
|-------|------|----------|
| Architecture Analyst | Phase 2 | 始终 |
| Convention Analyst | Phase 2 | 模块 >= 3 或源文件 >= 100 |
| Interface Extractor | Phase 4 | 始终 |
| Data Model Extractor | Phase 4 | 始终（与 Interface Extractor 并行）|
| Flow Analyst | Phase 5 | 始终 |

SubAgent prompt 结构：
1. 当前步骤的一句话描述
2. 前序 checkpoint 摘要（≤500字）
3. 指定 `Read references/code-analysis-pipeline.md` 对应阶段
4. 输出要求（产出写文件，返回文件列表+自评）

---

## 诚实性要求

- 不确定的信息标记 `[待确认]`
- 基于代码推断的结论标记 `[基于代码推断]`
- 不为凑分而降低质量标准