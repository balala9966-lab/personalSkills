# Auto-Recommend Rules

Given a piece of content, what preset to suggest first. Use these rules in `illustration-prompt-composer` Step 3 (Confirm) as the first option in the "preset" question.

## Detection Signals

Look at the article's first 1-3 paragraphs and the headings. Score by signal weight:

| Signal | Examples in article | Bumps content_type toward |
|--------|--------------------|--------------------------|
| API / SDK / endpoint / param | "the `/v1/messages` API supports …" | `technical` |
| Step / install / how to / 第一步 | "Step 1: install …" / "怎么配置" | `tutorial` |
| Architecture / system / module / component | "the ingestion pipeline has three stages" | `methodology` |
| Metric / % / N=/sample/dashboard / 同比 / 环比 | "MAU grew 23% QoQ" | `data` |
| vs / versus / compared to / pros and cons | "X vs Y", "tradeoffs between A and B" | `comparison` |
| I / my / when I / 我觉得 / 个人 | "I spent six months learning …" | `narrative` |
| Should / shouldn't / wrong / 反思 / 看法 | "Most engineering blogs get this wrong" | `opinion` |
| Year / decade / since / 历经 / 演进 | "from 1995 to today" | `history` |
| Hypothesis / experiment / result / 论文 | "we measured response time across …" | `academic` |
| User / pricing / onboarding / SaaS / product | "our new pricing tier launches …" | `saas` |

The highest-scoring `content_type` wins. Ties broken by the order above.

## Content Type → Preset

| content_type | First pick (auto-suggested) | Second pick (offered as alternate) |
|-------------|----------------------------|------------------------------------|
| `technical` | `tech-explainer` | `system-design` |
| `tutorial` | `tutorial` | `process-flow` |
| `methodology` | `system-design` | `architecture` |
| `data` | `data-report` | `versus` |
| `comparison` | `versus` | `business-compare` |
| `narrative` | `storytelling` | `lifestyle` |
| `opinion` | `opinion-piece` | `cinematic` |
| `history` | `history` | `evolution` |
| `academic` | `science-paper` | `tech-explainer` |
| `saas` | `saas-guide` | `knowledge-base` |
| *unknown / mixed* | `knowledge-base` | `tech-explainer` |

## Density Recommendation

Independent of preset, recommend density based on article length:

| Article word count | Recommended density |
|--------------------|--------------------|
| < 500 | `minimal` (1-2 images) |
| 500-1500 | `balanced` (3-5 images) |
| 1500-4000 | `per-section` (1 per H2) |
| > 4000 | `per-section` or `rich` (6+) |

For very short pieces, prefer one cover-quality image over multiple body images.

## Palette Recommendation

Use the rules in `palettes.md` "Auto-Pick Rules". If the preset already implies a palette (e.g. `edu-visual` → macaron, `ink-notes-compare` → mono-ink), use that and skip the palette question.

## When To Skip Auto-Recommend

- The user already specified `--preset X` explicitly.
- The user provided reference images — those should drive style/palette, not auto-recommend.
- The article uses an unusual register (e.g. fiction, satire, manifesto) — auto-recommend is calibrated for typical knowledge / opinion writing.
