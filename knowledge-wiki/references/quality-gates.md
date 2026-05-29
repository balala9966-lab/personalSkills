# Quality Gates

质量关卡应用于摄入和代码分析两个流程，确保 Wiki 页面的完整性和一致性。

---

## 业务摄入质量关卡

在每次摄入后对所有新建/更新的页面执行。

| 检查项 | 条件 | 失败动作 |
|--------|------|----------|
| **示例存在** | confidence >= medium 的概念页必须有 >=1 个具体示例 | 从源材料补充，或标记 `> [!question] Missing example` |
| **约束已记录** | 源材料提到约束/阈值时，对应 Wiki 页必须有 Constraints 章节 | 补充缺失约束 |
| **叙事保留** | 源材料有明显论证结构时，至少一个 Wiki 页捕获 "why" | 补充叙事到最相关的概念/主题页 |
| **风险分配** | 源材料描述责任/风险分配时，必须有页面显式记录 | 添加风险分配表 |
| **阈值值** | 源材料中的具体数字阈值必须出现在 Wiki 页面 | 添加到 Constraints 章节 |
| **演化记录** | 源材料描述版本历史/演化时，必须有页面捕获 Evolution 章节 | 添加演化链 |
| **对比分析** | 源材料显式对比 2+ 概念时，必须存在 analyses/ 对比页 | 创建或更新对比页 |

验证输出追加到 `log.md`：
```
[YYYY-MM-DD] Quality validation for {source-name}: {N} checks passed, {M} gaps found and remediated
```

---

## 代码分析质量关卡

在代码分析 Phase 6 终审时执行。**强卡点**：不通过不允许结束。

### Phase 2 关卡：架构分析

| 检查项 | 通过条件 |
|--------|----------|
| 架构描述准确 | 系统分层、模块划分与代码结构一致 |
| 约定识别完整 | 命名规范、分层规则、错误处理模式已记录 |

### Phase 3 关卡：模块索引

| 检查项 | 通过条件 |
|--------|----------|
| 模块覆盖 | 所有识别的模块在 _index.md 中有条目 |
| 业务链接 | 每个模块至少有一个业务概念 wikilink |

### Phase 4 关卡：接口与模型

| 检查项 | 通过条件 |
|--------|----------|
| 接口覆盖 | 所有 public 接口在 interfaces/ 中有记录 |
| 模型覆盖 | 所有核心数据模型在 data-models/ 中有记录 |
| 签名准确 | 接口方法签名与代码一致 |

### Phase 5 关卡：流程与关系

| 检查项 | 通过条件 |
|--------|----------|
| 流程覆盖 | 核心业务流程已在 flows/ 中记录 |
| 依赖完整 | 外部依赖已在 dependencies.md 中列出 |
| 术语表 | 技术术语已在 glossary.md 中定义 |

### Phase 6 关卡：终审（强卡点）

| 检查项 | 通过条件 |
|--------|----------|
| 模块覆盖率 | >= 90% |
| 接口覆盖率 | >= 80% |
| 模型覆盖率 | >= 80% |
| 业务链接率 | 每个代码页至少 1 个业务 wikilink |
| Frontmatter 一致性 | 所有页面包含必填 YAML 字段 |
| 索引更新 | index.md 和 AGENTS.md 已更新 |

---

## Lint 质量关卡

在 `kb-lint` 命令时执行。

| 检查类别 | 检查内容 | 严重级别 |
|----------|---------|----------|
| 矛盾检测 | 不同页面对同一事实的矛盾描述 | ERROR |
| 断链检测 | 指向不存在页面的 wikilink | ERROR |
| 孤岛页面 | 无入站 wikilink 的页面（maps/ 除外） | WARNING |
| 概念缺页 | 被提及 >=3 次但无独立页面 | INFO |
| 缺失交叉引用 | 相关页面间缺少 wikilink | INFO |
| Frontmatter 一致性 | 页面缺少必填 YAML 字段 | WARNING |
| 源覆盖度 | raw/ 中已有但未摄入 wiki 的源 | INFO |
| 源保留一致性 | 源页面的 preservation 字段与 .kb-state.json 不一致 | WARNING |
| 源不可达 | link 保留方式的源在远端不可达 | WARNING |
| SHA-256 哈希缺失 | source_registry 中缺少 sha256 字段 | INFO |
| 代码页覆盖度 | 已注册仓库但未生成 wiki/code/ 页面 | WARNING |
| 代码同步度 | 代码页与仓库最新 commit 的偏差 | INFO |
| 业务-代码脱节 | 代码页无业务链接或业务页无代码链接 | WARNING |
| 图谱边缺失 | 高度相关但未建立 wikilink 的页面对 | INFO |
| AMBIGUOUS 边过期 | 长期未确认的 AMBIGUOUS 边（>30 天） | INFO |
| 合成页级联缺失 | synthesis 页的 cascade 字段中引用的页面不存在 | WARNING |

---

## 质量评分

每次 lint 或终审后计算质量评分：

```
Score = (passed_checks / total_checks) * 100

评级：
  A: 90-100  — 优秀
  B: 80-89   — 良好
  C: 70-79   — 可接受
  D: 60-69   — 需改进
  F: <60     — 不合格
```

评分记录到 `.kb-state.json` 的 `lint_stats` 中。