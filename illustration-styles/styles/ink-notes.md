---
id: ink-notes
family: hand-drawn
---

# Ink Notes

Pure white background, black ink, sparse semantic accent colors. The visual-essay register — close cousin of the standalone `editorial-illustration` skill in this repo.

## Visual Traits

- **Line work**: thin black hand-drawn line with slight organic wobble
- **Fill**: usually none; occasional flat accent fill in red, orange, or blue
- **Background**: pure white, no texture
- **Color discipline**: black dominant + 1-3 semantic accents (red = problem/outcome, orange = flow/movement, blue = secondary/system state)
- **Typography**: handwritten labels, sparse, 5-8 spots max
- **Composition**: subject 40-60% of frame, at least 35% whitespace including one quiet area

## Best For

- `infographic`, `comparison`, `framework` — when you want a visual essay, not an infographic
- Manifestos, opinion-with-structure, "the X anatomy of Y" pieces

## Avoid For

- `scene` — too sparse for narrative
- `flowchart` with many steps — gets cluttered

## Canonical Palette

Pairs best with: `mono-ink` (this is the palette it was designed for). The accent colors *are* the palette discipline.

## Generation Prompt Hints

Include:
- "pure white background"
- "thin black hand-drawn line work with slight wobble"
- "lots of whitespace, restrained"
- "sparse handwritten annotations"
- "small red / orange / blue accent details"

Avoid:
- "filled illustration", "colorful", "vibrant"
- "PPT slide", "infographic boxes", "flowchart with rectangles"
- "polished vector"

## Extended Methodology

The `ink-notes` style ships with a deep methodology that makes it a full replacement for standalone editorial-illustration skills:

- **`ink-notes-extended/composition-patterns.md`** — 10 structural patterns (Threshold, Split Path, Loop, Compression, Translation, Balance, Excavation, Relay, Repair, Mismatch) + metaphor invention rules + anti-repetition list
- **`ink-notes-extended/default-ip.md`** — The Tinkerer character spec + user-supplied IP replacement rules + custom_ip config schema
- **`ink-notes-extended/qa-checklist.md`** — Full post-generation quality checklist with regeneration rules

When `illustration-prompt-composer` selects `ink-notes` as the style, it should also load these extended files to get:
1. The composition pattern dictionary (for outline step — picks the right visual structure)
2. The default IP description (for prompt composition — embeds character traits)
3. The QA checklist (for post-generation verification)

This makes the full `antintl-mascot-illustration` / `editorial-illustration` methodology available as a style within the unified system, without needing a separate skill installed.
