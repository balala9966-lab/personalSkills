# {kb-name} - Schema for Claude Code

## First Read
**每次操作前，先读 `README.md`**——这是用户编写的知识库说明书，包含领域描述、重点关注方向和偏好。README.md 的内容决定摄入优先级、查询侧重和 explore 建议。

## KB Structure
三层架构：
- `raw/` — 原始源文档（不可变，LLM 只读）
  - `raw/business/` — 业务源（web/、yuque/、feishu/、local/）
  - `raw/code/` — 代码仓库引用（repo-meta.json，不放代码本身）
- `wiki/` — Wiki 页面（LLM 生成维护）
  - 业务域：entities/、concepts/、topics/、sources/、analyses/、maps/
  - 代码域：code/architecture/、code/modules/、code/interfaces/、code/data-models/、code/flows/、code/contracts/
  - 跨域：changelog/
- `.schema/` — 配置（用户 + LLM 共同演进）

## Navigation Workflow
1. **Always read `wiki/AGENTS.md` first** — 精简导航，避免遍历整个知识库
2. Follow `[[wikilinks]]` to relevant pages
3. For large KB: use qmd search/vsearch/query
4. For code queries: check `wiki/code/modules/_index.md` first

## Ingest Workflow
1. Route source to adapter (see `.schema/source-adapters.md`)
2. Save raw source to `raw/{adapter}/`
3. Read and extract entities/concepts
4. Create/update wiki pages with cross-references
5. Update `wiki/index.md`, `wiki/AGENTS.md`, and `log.md`
6. Run qmd embed if available
7. Git commit

## Code Analysis Workflow
1. Clone or reference code repository
2. Run 6-phase pipeline (see code-analysis-pipeline.md)
3. Output to `wiki/code/` with proper frontmatter and wikilinks
4. Link code pages to business pages (and vice versa)
5. Update `wiki/index.md` and `wiki/AGENTS.md`
6. Update `.codewiki-meta.json`

## Page Update Rules
- Preserve YAML frontmatter
- Use `[[wikilinks]]` for cross-references
- Update `updated` date field
- Add new sources to `sources` list
- Maintain existing content, append new information
- **Always add Business Context / Code Implementation links** when relevant

## Source Adapters
{adapter-configs}

## Associated Code Repos
{code-repos-section}

## Sync Targets
{sync-targets-section}

## qmd Commands
{qmd-commands}

## Domain Conventions
{domain-context}