# Wiki Page Frontmatter Templates

Quick-reference frontmatter templates for each page type.

---

## Entity Page

```yaml
---
title: "{Entity Name}"
type: entity
tags:
  - domain/{domain}
  - type/entity
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
sources:
  - "[[source-page]]"
aliases:
  - "{Alternative Name}"
status: active
confidence: high
---
```

## Concept Page

```yaml
---
title: "{Concept Name}"
type: concept
tags:
  - domain/{domain}
  - type/concept
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
sources:
  - "[[source-page]]"
aliases:
  - "{Alternative Term}"
status: active
confidence: medium
---
```

## Topic Page

```yaml
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
```

## Source Page

```yaml
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
```

## Analysis Page

```yaml
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
```

## Map Page

```yaml
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
```

## Architecture Page

```yaml
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
```

## Flow Page

```yaml
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
```

## Changelog Page

```yaml
---
title: "Changelog: {description}"
type: changelog
date: {YYYY-MM-DD}
sources:
  - "[[source-page]]"
---
```

## Index Page

```yaml
---
title: "{KB Name} Index"
type: index
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
tags:
  - index
  - navigation
status: active
---
```

## Overview Page

```yaml
---
title: "{KB Name} Overview"
type: overview
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
tags:
  - overview
confidence: medium
status: draft
scope: "High-level overview of the {KB Name} knowledge base"
---
```

## Synthesis Page

```yaml
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
  - "[[source-page]]"
cascade:
  created_pages:
    - "[[{new-page}}]]"
  updated_pages:
    - "[[{existing-page}}]]"
---
```