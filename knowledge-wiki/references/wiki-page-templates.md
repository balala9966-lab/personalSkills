# Wiki Page Templates

每个 Wiki 页面类型有定义的结构。所有模板包含 Obsidian 兼容的 YAML frontmatter。

---

## Entity Page — `wiki/entities/{name}.md`

适用于：组织、系统、API、渠道、产品。

```markdown
---
title: "{Entity Name}"
type: entity
tags:
  - domain/{domain}
  - type/entity
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
sources:
  - "[[source-page-1]]"
aliases:
  - "{Alternative Name}"
status: active
confidence: high
---

# {Entity Name}

## Overview
Brief description of what this entity is, its role, and significance.

## Key Attributes
| Attribute | Value |
|---|---|
| Full Name | {full official name} |
| Type | {organization / system / API / channel} |
| Region | {operating region} |
| Status | {active / deprecated / planned} |

## Relationships
- **Parent**: [[{Parent Entity}]]
- **Subsidiaries**: [[{Child Entity 1}]], [[{Child Entity 2}]]
- **Integrates with**: [[{Related System}]]

## Code Implementation
- [[code/modules/{module}|{ModuleName}]] — {how this entity is implemented}
- [[code/interfaces/{interface}|{InterfaceName}]] — {related interface}

## Constraints & Compliance
- **Licensing requirements**: {required licenses}
- **Regulatory obligations**: {applicable regulations}
- **Operational limits**: {transaction limits, geographic restrictions}

## History / Timeline
| Date | Event | Business Reason |
|---|---|---|
| {YYYY-MM-DD} | {event} | {why} |

## Related Pages
- [[{related-concept}]]
- [[{related-topic}]]

## Sources
- [[{source-summary-page-1}]]
```

---

## Concept Page — `wiki/concepts/{name}.md`

适用于：模式、原则、协议、方法论。

```markdown
---
title: "{Concept Name}"
type: concept
tags:
  - domain/{domain}
  - type/concept
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
sources:
  - "[[source-page-1]]"
aliases:
  - "{Alternative Term}"
status: active
confidence: medium
---

# {Concept Name}

## Definition
A clear, concise definition in 1-3 sentences.

## Context
Where this concept applies, why it matters.

## Why This Exists
Business rationale: what problem it solves, what drove its creation.

## How It Works
Step-by-step explanation of the mechanism.

## Constraints & Edge Cases
- **Regulatory limits**: {regulations}
- **Operational restrictions**: {throughput limits, etc.}
- **Failure modes**: {conditions under which this breaks down}
- **Numerical thresholds**: {specific limits}

## Evolution
How this concept has changed over time.

## Examples
### Example 1: {scenario name}
{Concrete example from source material}

## Code Implementation
- [[code/modules/{module}|{ModuleName}]] — {implementation details}
- [[code/flows/{flow}|{FlowName}]] — {where this concept manifests}

## Related Concepts
- [[{related-concept-1}]] — {how it relates}

## Sources
- [[{source-summary-page-1}]]
```

---

## Topic Page — `wiki/topics/{name}.md`

适用于：领域分区 hub 页。

```markdown
---
title: "{Topic Name}"
type: topic
tags:
  - domain/{domain}
  - type/topic
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: active
---

# {Topic Name}

## Overview
High-level summary of this domain area.

## Key Concepts
- [[{concept-1}]] — {brief description}

## Key Entities
- [[{entity-1}]] — {brief description}

## Code Modules
- [[code/modules/{module}|{ModuleName}]] — {brief description}

## Current State
- What's working well
- What's changing
- What's planned

## Open Questions
> [!question] {Question 1}
> {Details}

## Related Topics
- [[{related-topic-1}]]

## Sources
- [[{source-summary-1}]]
```

---

## Source Summary Page — `wiki/sources/source-{name}.md`

每个摄入源对应一个摘要页。

```markdown
---
title: "Source: {Source Title}"
type: source
tags:
  - source/{source-type}
  - domain/{domain}
source_url: "{original URL or file path}"
source_type: "{web|yuque|feishu|youtube|arxiv|rss|jupyter|pptx|csv|local-markdown|local-pdf|local-docx|github|git}"
direct_link: "{relative path from KB root to raw source file}"
adapter: "{adapter name}"
preservation: "{local|link}"
ingested_at: {YYYY-MM-DD}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: active
---

# {Source Title}

## Direct Link
`{relative/path/to/raw/source/file}`

## Summary
Comprehensive summary of the source document.

## Narrative Thread
{3-5 sentences describing the source's main argument/story flow}

## Key Takeaways
- {Takeaway 1}
- {Takeaway 2}

## Entities Mentioned
- [[{Entity 1}]] — {context}

## Concepts Introduced
- [[{Concept 1}]] — {how this source defines it}

## Notable Claims
| Claim | Confidence | Notes |
|---|---|---|
| {claim} | high/medium/low | {evidence} |

## Constraints & Risks Documented
| Constraint / Risk | Type | Details |
|---|---|---|
| {constraint} | regulatory/operational/technical | {details} |

## Cross-references to Updated Pages
- [[{entity-page}]] — added {what was added}
- [[{concept-page}]] — created from this source
```

---

## Analysis Page — `wiki/analyses/{topic}.md`

查询归档和对比分析。

```markdown
---
title: "{Analysis Title}"
type: analysis
tags:
  - domain/{domain}
  - type/analysis
query: "{original user question}"
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: active
confidence: medium
---

# {Analysis Title}

## Question
{The original question}

## Methodology
1. **Sources consulted**: {number} wiki pages, {number} raw sources
2. **Search strategy**: {keyword / semantic / hybrid}

## Findings
### Finding 1: {title}
{Detailed finding with evidence}

### Finding 2: {title}
{Detailed finding}

## Conclusion
{Synthesized answer}

## Recommendations
1. {Actionable recommendation}

## Sources Consulted
- [[{wiki-page-1}]] — {what it contributed}
```

---

## Comparison / Analysis Page — `wiki/analyses/{topic}-comparison.md`

源文档显式对比时触发。

```markdown
---
title: "{Topic A} vs {Topic B} Comparison"
type: analysis
tags: [domain/..., type/comparison]
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
sources:
  - "[[source-page]]"
confidence: high
---

# {Topic A} vs {Topic B} Comparison

## Overview
Why this comparison matters.

## Comparison Matrix
| Dimension | {Topic A} | {Topic B} |
|---|---|---|
| {dim 1} | {value} | {value} |

## When to Use Each
Decision criteria and use-case mapping.

## Key Trade-offs
What you gain vs. lose with each approach.

## Related Pages
- [[{concept-a}]]
- [[{concept-b}]]
```

---

## Map Page — `wiki/maps/{name}.md`

关系图谱页面（借鉴 localwiki）。

```markdown
---
title: "{Map Title}"
type: map
tags:
  - domain/{domain}
  - type/map
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: active
---

# {Map Title}

## Overview
What this map visualizes and why it matters.

## Relationship Graph

\`\`\`mermaid
graph TD
    A[[Entity A]] --> B[[Entity B]]
    B --> C[[Concept C]]
    C --> D[[Entity D]]
\`\`\`

## Key Relationships
| From | To | Relationship | Context |
|---|---|---|---|
| [[Entity A]] | [[Entity B]] | depends on | {context} |

## Gaps
- [[Entity D]] has no inbound links from business pages
- [[Concept C]] is mentioned but not yet documented

## Related Pages
- [[{related-topic}]]
```

---

## Architecture Page — `wiki/code/architecture/{system-name}.md`

```markdown
---
title: "{System Name} Architecture"
type: architecture
tags:
  - domain/{domain}
  - type/architecture
repo: "[[{code-repo-entity}]]"
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: active
confidence: medium
---

# {System Name} Architecture

## System Overview
High-level description, architectural style.

## Components
| Component | Purpose | Technology | Location |
|---|---|---|---|
| {comp-1} | {what} | {tech} | `{path}` |

## Data Flow
\`\`\`
{Component A} → {Component B} → {Component C}
\`\`\`

## Integration Points
| Integration | Protocol | Direction | Partner |
|---|---|---|---|
| {int-1} | REST/gRPC/MQ | inbound/outbound | [[{partner}]] |

## Dependencies
- **Internal**: [[{internal-service-1}]]
- **External**: [[{external-api-1}]]

## Business Context
- [[{business-concept-1}]] — {how this system implements it}
- [[{business-concept-2}]] — {related business flow}

## Code References
- Repository: [[{code-repo-entity}]]
- Entry point: `{path/to/main}`
```

---

## Module Index — `wiki/code/modules/_index.md`

```markdown
---
title: "Module Index"
type: index
domain: code
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
---

# Module Index

| Module | Responsibility | Path | Key Interfaces | Business Concepts |
|--------|---------------|------|----------------|-------------------|
| {module-1} | {desc} | {path} | {iface-list} | [[{concept}]] |
```

---

## Interface Index — `wiki/code/interfaces/_index.md`

```markdown
---
title: "Interface Index"
type: index
domain: code
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
---

# Interface Index

## {Group Name}
| Interface | Type | Module | Methods | Business Concept |
|-----------|------|--------|---------|------------------|
| {Iface} | Facade/RpcService/Controller/SPI | {module} | {count} | [[{concept}]] |
```

---

## Flow Page — `wiki/code/flows/{flow-name}.md`

```markdown
---
title: "{Flow Name}"
type: flow
tags:
  - domain/{domain}
  - type/flow
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: active
---

# {Flow Name}

## Trigger
What initiates this flow.

## Participants
- [[code/modules/{module-1}|{Module1}]] — {role}
- [[code/modules/{module-2}|{Module2}]] — {role}

## Data Flow
\`\`\`
{Step 1} → {Step 2} → {Step 3}
\`\`\`

## Business Context
- [[{business-concept}]] — {how this flow relates}

## Error Handling
How errors are handled at each step.

## Related Pages
- [[code/architecture/{system}|{System} Architecture]]
```

---

## Changelog Page — `wiki/changelog/{date}-{source}.md`

```markdown
---
title: "Changelog: {description}"
type: changelog
date: {YYYY-MM-DD}
sources:
  - "[[source-page]]"
---

# Changelog: {description}

## Summary
What changed and why.

## Changes
| Page | Change Type | Description |
|------|------------|-------------|
| [[{page}]] | created/updated | {what changed} |

## Impact
Which pages may need review as a result.
```

---

## Synthesis Page — `wiki/analyses/synthesis-{topic}.md`

查询结果沉淀页。当用户选择将查询结果归档时自动创建，触发级联更新。

```markdown
---
title: "Synthesis: {Topic}"
type: synthesis
tags:
  - domain/{domain}
  - type/synthesis
query: "{original user question}"
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: active
confidence: medium
sources:
  - "[[source-page-1]]"
cascade:
  created_pages:
    - "[[{new-entity-or-concept-page}}]]"
  updated_pages:
    - "[[{existing-page-updated}}]]"
---

# Synthesis: {Topic}

## Original Question
{The user's original query}

## Synthesized Answer
{Comprehensive answer drawing from multiple wiki pages and raw sources}

## Key Insights
- {Insight 1 with evidence from [[page-a]]}
- {Insight 2 with evidence from [[page-b]]}

## Knowledge Gaps
- [ ] {Gap 1}: {what we couldn't answer}
- [ ] {Gap 2}: {what needs more sources}

## Pages Created
- [[{new-page-1}]] — {why it was needed}
- [[{new-page-2}]] — {why it was needed}

## Pages Updated
- [[{existing-page-1}]] — {what was added/changed}
- [[{existing-page-2}]] — {what was added/changed}

## Sources Consulted
- [[{source-1}]] — {contribution}
- [[{source-2}]] — {contribution}
```

**级联更新规则**（创建合成页时自动触发）：
1. 扫描合成页中所有 `[[wikilinks]]`
2. 目标页面已存在 → 更新其交叉引用章节
3. 目标页面不存在 → 创建占位实体/概念页（`status: draft`）
4. 更新 `wiki/index.md`（Analyses 分区 + 新创建的占位页）
5. 更新 `wiki/overview.md`（如合成页涉及全局知识）
6. 更新 `graph/graph.json`（新增边）