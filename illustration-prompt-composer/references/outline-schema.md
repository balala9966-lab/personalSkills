# Outline Schema

The outline document drives everything downstream. `plan.py` writes it from the article + user choices; `compose.py` reads it to produce prompt files; `dispatch.py` reads it to know what to render; `writeback.py` reads it to know where to insert images.

## File Location

`{output_root}/{article_slug}/outline.md`

## Frontmatter

```yaml
---
article_slug: my-article             # required, identifies the working directory
type: infographic                    # required, one of the 6 types from illustration-styles
style: blueprint                     # required, one of the 23 styles
palette: cool                        # optional, falls back to style's canonical palette
density: balanced                    # minimal | balanced | per-section | rich
image_count: 4                       # required, == number of body ## blocks
mode: illustration                   # illustration | cover | both
language: en                         # default label language for generated images
backend: openai_images               # optional, overrides EXTEND.md default for this article
model: gpt-image-1                   # optional, overrides backend default
aspect: 16:9                         # optional, default 16:9 for body, set per-mode for cover
references:                          # only if real reference files exist
  - ref_id: 01
    filename: 01-ref-diagram.png
    description: technical diagram showing system architecture
---
```

## Per-Illustration Block

Each `##` heading is one illustration. Block fields:

| Field | Required | Notes |
|-------|----------|-------|
| `**Position**:` | yes | `<section name> / <paragraph snippet or anchor>` — used by writeback to locate insertion point |
| `**Purpose**:` | yes | One-sentence justification — why this image earns its place |
| `**Visual Content**:` | yes | Bullet list, one visual element per line, each starting with `- ` |
| `**Type Application**:` | recommended | How the chosen Type expresses this concept |
| `**References**:` | optional | `[01, 02]` — ref_ids from frontmatter, only when actual files exist |
| `**Reference Usage**:` | optional | `direct` / `style` / `palette` — how downstream should use the refs |
| `**Filename**:` | yes | `NN-<type>-<slug>.png` — must be unique within the article |

## Cover Block (mode=cover or mode=both)

```markdown
## Cover

**Type**: hero|conceptual|typography|metaphor|scene|minimal
**Style**: <style-id>     # may differ from body style
**Palette**: <palette-id>
**Title**: <article title from the source, do not invent>
**Subtitle**: <optional>
**Text Level**: title-only|title-subtitle|none
**Mood**: subtle|balanced|bold
**Aspect**: 16:9
**Visual Content**:
- <element 1>
- <element 2>
**Filename**: cover.png
```

## Formatting Rules

- Blocks separated by blank lines.
- Field labels on their own line, content on the next line.
- `Visual Content` always uses bullet-list format, never a comma-separated string — downstream scripts split on `\n- `.
- Filenames are kebab-case, lowercase, ASCII-safe.
- Do not put markdown inside field values (no `**bold**`, no links).

## Example

```yaml
---
article_slug: rate-limiter-design
type: framework
style: blueprint
palette: cool
density: balanced
image_count: 3
mode: illustration
language: en
aspect: 16:9
---

## Illustration 1

**Position**: Introduction / "the burst problem"

**Purpose**: Show the gap between average and peak request rates that motivates a rate limiter.

**Visual Content**:
- Two side-by-side line charts: smooth average vs spiky peaks
- Annotation arrow pointing at the largest spike: "this is the request that breaks production"
- Faint horizontal line marking the system's safe capacity

**Type Application**: Framework — two related visualizations sharing a common Y-axis (request rate).

**Filename**: 01-framework-burst-problem.png

## Illustration 2

**Position**: "Token bucket algorithm" / first paragraph

**Purpose**: Make the token-bucket mechanic visible before diving into pseudocode.

**Visual Content**:
- A bucket with discrete tokens accumulating
- A faucet labeled "refill rate: 100/s" dripping tokens in
- Requests entering as small arrows, each taking a token; an arrow blocked when the bucket is empty
- Labels: "capacity: 200", "burst tolerance"

**Type Application**: Framework — components (bucket / faucet / requests) with their relationships shown.

**Filename**: 02-framework-token-bucket.png

## Illustration 3

**Position**: Comparison section / "leaky bucket vs token bucket"

**Purpose**: Show why the team picked token bucket over the alternative.

**Visual Content**:
- Two buckets side by side
- Left: leaky bucket — fixed output rate, queue builds up
- Right: token bucket — burst-friendly, idle periods refill tokens
- Verdict callout under each: "smooths but adds latency" / "allows controlled bursts"

**Type Application**: Framework as comparison — two parallel mechanisms with the same axes.

**Filename**: 03-framework-leaky-vs-token.png
```
