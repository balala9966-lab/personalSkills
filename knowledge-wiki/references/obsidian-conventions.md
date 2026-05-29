# Obsidian Conventions

## YAML Frontmatter Schema

每个 Wiki 页面必须包含 YAML frontmatter。必填字段因页面类型而异。

### 通用必填字段

```yaml
---
title: "{Page Title}"
type: entity|concept|topic|source|analysis|map|architecture|index|flow|changelog
tags:
  - "domain/{domain}"
  - "type/{sub-type}"
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: active|draft|deprecated
---
```

### 按类型额外字段

| 字段 | 适用类型 | 说明 |
|------|---------|------|
| `sources` | entity, concept, source, analysis | 来源页面列表 |
| `aliases` | entity, concept | 别名列表 |
| `confidence` | entity, concept, analysis | high/medium/low |
| `source_url` | source | 原始 URL |
| `source_type` | source | 适配器名称 |
| `direct_link` | source | raw/ 路径 |
| `adapter` | source | 使用的适配器 |
| `ingested_at` | source | 摄入日期 |
| `query` | analysis | 原始查询问题 |
| `repo` | architecture | 关联代码仓库 |
| `affected_systems` | changelog | 受影响系统 |

---

## Wikilinks

- 页面间交叉引用**必须**使用 `[[Page Name]]` 格式
- 支持 `[[Page Name|Display Text]]` 别名链接
- 支持 `[[Page Name#Section]]` 章节链接
- **禁止**使用 Markdown `[text](url)` 链接引用 Wiki 内部页面
- 代码页与业务页之间的链接是强制性的（质量关卡检查）

---

## Tags

- 使用 `#tag` 格式，支持层级标签
- 标准标签前缀：

| 前缀 | 用途 | 示例 |
|------|------|------|
| `#domain/` | 业务领域 | `#domain/payment`, `#domain/settlement` |
| `#type/` | 页面子类型 | `#type/entity`, `#type/concept`, `#type/code/interface` |
| `#status/` | 状态标记 | `#status/active`, `#status/deprecated` |
| `#source/` | 来源类型 | `#source/yuque`, `#source/github` |
| `#code/` | 代码相关 | `#code/java`, `#code/spring-boot` |

---

## Dataview 兼容

Frontmatter 字段可被 Obsidian Dataview 插件查询：

```dataview
TABLE type, updated, length(sources) as "Source Count"
FROM "wiki"
WHERE type = "entity"
SORT updated DESC
```

```dataview
TABLE type, confidence
FROM "wiki/code"
SORT updated DESC
```

---

## Graph View 优化

- 通过丰富的 wikilink 互链提升图谱可视化效果
- 每个页面至少有 1 个入站链接（maps/ 除外）
- 实体页之间建立关联链接（上下游系统、依赖关系）
- **代码页必须链接到至少 1 个业务页面**，反之亦然
- maps/ 页面作为关系枢纽，集中展示复杂关系

---

## Callout Blocks

| 类型 | 用途 |
|------|------|
| `> [!info]` | 补充信息 |
| `> [!warning]` | 风险警告 |
| `> [!tip]` | 最佳实践建议 |
| `> [!question]` | 待确认/待补充 |
| `> [!success]` | 已验证结论 |
| `> [!danger]` | 严重风险/已知问题 |
| `> [!note]` | 来源视角标注 |

---

## Marp 演示支持

Wiki 内容可导出为 Marp 格式用于演示（在 analyses/ 中生成 slide deck）。

---

## 命名规范

- 文件名使用 kebab-case：`settlement-cycle.md`，不用空格
- 页面标题使用 Title Case 或自然语言：`Settlement Cycle` 或 `结算周期`
- 目录名使用 kebab-case：`code/data-models/`
- Source 页面前缀：`source-{name}.md`
- Changelog 页面日期前缀：`2026-05-14-settlement-update.md`