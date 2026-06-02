# Presets

19 named Type+Style combos for common content categories. A preset is a *shortcut*: instead of choosing a Type and a Style separately, pick a preset that bundles both — with an opinion baked in about which combo works for the use case.

You can always override either dimension after picking a preset (e.g. `--preset tech-explainer --style notion`).

## Technical & Engineering

| Preset | Type | Style | Use case |
|--------|------|-------|----------|
| `tech-explainer` | `infographic` | `blueprint` | API docs, system metrics, technical deep-dives |
| `system-design` | `framework` | `blueprint` | Architecture diagrams, system design articles |
| `architecture` | `framework` | `vector-illustration` | Component relationships, module structure |
| `science-paper` | `infographic` | `scientific` | Research findings, experiment results, papers |

## Knowledge & Education

| Preset | Type | Style | Use case |
|--------|------|-------|----------|
| `knowledge-base` | `infographic` | `vector-illustration` | Concept explanations, tutorials, how-tos |
| `saas-guide` | `infographic` | `notion` | Product guides, SaaS docs, tool tutorials |
| `tutorial` | `flowchart` | `vector-illustration` | Step-by-step guides, installation walkthroughs |
| `process-flow` | `flowchart` | `notion` | Workflow docs, onboarding flows |
| `edu-visual` | `infographic` | `vector-illustration` (palette: macaron) | Knowledge summaries, educational articles |
| `hand-drawn-edu` | `flowchart` | `sketch-notes` (palette: macaron) | Hand-drawn educational diagrams |
| `ink-notes-compare` | `comparison` | `ink-notes` (palette: mono-ink) | Before/after, traditional vs new |

## Data & Analysis

| Preset | Type | Style | Use case |
|--------|------|-------|----------|
| `data-report` | `infographic` | `editorial` | Data reporting, metric reports, dashboards |
| `versus` | `comparison` | `vector-illustration` | Technical comparison, framework face-offs |
| `business-compare` | `comparison` | `elegant` | Product evaluation, strategy options |

## Narrative & Creative

| Preset | Type | Style | Use case |
|--------|------|-------|----------|
| `storytelling` | `scene` | `warm` | Personal essays, reflections, growth stories |
| `lifestyle` | `scene` | `watercolor` | Travel, wellness, lifestyle, creative |
| `history` | `timeline` | `elegant` | History overviews, milestones |
| `evolution` | `timeline` | `warm` | Progress narratives, growth journeys |

## Opinion & Editorial

| Preset | Type | Style | Use case |
|--------|------|-------|----------|
| `opinion-piece` | `scene` | `screen-print` | Commentary, critical pieces |
| `editorial-poster` | `comparison` | `screen-print` | Debates, opposing viewpoints |
| `cinematic` | `scene` | `screen-print` | Dramatic narrative, cultural essays |

## Content Type → Preset

| Content type | First pick | Alternates |
|--------------|-----------|------------|
| Technical | `tech-explainer` | `system-design`, `architecture` |
| Tutorial | `tutorial` | `process-flow`, `knowledge-base` |
| Methodology / framework | `system-design` | `architecture`, `process-flow` |
| Data / metrics | `data-report` | `versus`, `tech-explainer` |
| Comparison / review | `versus` | `business-compare`, `editorial-poster` |
| Narrative / personal | `storytelling` | `lifestyle`, `evolution` |
| Opinion / editorial | `opinion-piece` | `cinematic`, `editorial-poster` |
| History / timeline | `history` | `evolution` |
| Academic / research | `science-paper` | `tech-explainer`, `data-report` |
| SaaS / product | `saas-guide` | `knowledge-base`, `process-flow` |

## Override Examples

- `--preset tech-explainer --style notion` → Type from preset (`infographic`), Style overridden to `notion`
- `--preset storytelling --type timeline` → Style from preset (`warm`), Type overridden to `timeline`

Explicit `--type` / `--style` always overrides the preset's value.
