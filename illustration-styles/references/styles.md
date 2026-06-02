# Styles

23 visual styles, grouped into 6 families. Each family shares a common visual register; pick the family that matches the article's voice, then pick the specific style for finer control.

For Style × Type compatibility see `compatibility.md`. For preset shortcuts (e.g. `tech-explainer` = `infographic` + `blueprint`) see `presets.md`.

## Families

| Family | Voice | When to reach for it |
|--------|-------|---------------------|
| Flat | Clean, modern, brand-safe | Knowledge articles, SaaS, product writing |
| Hand-drawn | Warm, personal, exploratory | Reflections, opinion, learning notes |
| Technical | Precise, diagrammatic, engineering-flavoured | System design, architecture, research |
| Artistic | Painterly, atmospheric, evocative | Lifestyle, travel, fiction, creative work |
| Poster | Bold, graphic, opinionated | Cultural commentary, op-eds, manifestos |
| Special | Genre-specific, distinctive | Pixel art, vintage, etc. — use intentionally |

## All Styles

### Flat family

| Style | Description | Detail |
|-------|-------------|--------|
| `vector-illustration` | Clean flat vector art with bold shapes | [styles/vector-illustration.md](../styles/vector-illustration.md) |
| `notion` | Minimal hand-drawn line art, neutral palette | [styles/notion.md](../styles/notion.md) |
| `flat` | Modern geometric flat with bold shapes | [styles/flat.md](../styles/flat.md) |
| `flat-doodle` | Cute flat with thick outlines | [styles/flat-doodle.md](../styles/flat-doodle.md) |
| `minimal` | Ultra-clean, lots of whitespace, zen | [styles/minimal.md](../styles/minimal.md) |

### Hand-drawn family

| Style | Description | Detail |
|-------|-------------|--------|
| `sketch` | Raw pencil-notebook feel | [styles/sketch.md](../styles/sketch.md) |
| `sketch-notes` | Soft hand-drawn warm notes | [styles/sketch-notes.md](../styles/sketch-notes.md) |
| `warm` | Friendly, approachable, soft palette | [styles/warm.md](../styles/warm.md) |
| `playful` | Whimsical pastel doodles | [styles/playful.md](../styles/playful.md) |
| `ink-notes` | Pure white background, black ink, sparse semantic accent colors | [styles/ink-notes.md](../styles/ink-notes.md) |

### Technical family

| Style | Description | Detail |
|-------|-------------|--------|
| `blueprint` | Technical schematic / engineering blueprint feel | [styles/blueprint.md](../styles/blueprint.md) |
| `scientific` | Academic precision, lab-figure feel | [styles/scientific.md](../styles/scientific.md) |
| `editorial` | Magazine-style infographic | [styles/editorial.md](../styles/editorial.md) |
| `chalkboard` | Classroom chalkboard / handwritten explanation | [styles/chalkboard.md](../styles/chalkboard.md) |

### Artistic family

| Style | Description | Detail |
|-------|-------------|--------|
| `watercolor` | Soft artistic watercolor washes | [styles/watercolor.md](../styles/watercolor.md) |
| `elegant` | Refined, polished, editorial-grade | [styles/elegant.md](../styles/elegant.md) |
| `nature` | Organic earth-tone illustration | [styles/nature.md](../styles/nature.md) |
| `fantasy-animation` | Ghibli / animation-studio storybook feel | [styles/fantasy-animation.md](../styles/fantasy-animation.md) |

### Poster family

| Style | Description | Detail |
|-------|-------------|--------|
| `screen-print` | Bold poster art with halftone textures, limited colors | [styles/screen-print.md](../styles/screen-print.md) |
| `retro` | 80s/90s neon geometric | [styles/retro.md](../styles/retro.md) |

### Special family

| Style | Description | Detail |
|-------|-------------|--------|
| `pixel-art` | Retro 8-bit game aesthetic | [styles/pixel-art.md](../styles/pixel-art.md) |
| `vintage` | Aged parchment, historical feel | [styles/vintage.md](../styles/vintage.md) |
| `intuition-machine` | Technical briefing on aged paper | [styles/intuition-machine.md](../styles/intuition-machine.md) |

## Picking A Style

Read the article's first three paragraphs. Two questions:

1. **What register?** (precise / warm / opinionated / artistic / playful)
2. **What does the reader's eye need?** (lots of structure / lots of breathing room / lots of mood)

Then pick a family, then a specific style. If unsure between two in the same family, `compatibility.md` will tell you which works better with your chosen Type.

## Anti-Patterns

- Using `playful` or `fantasy-animation` for technical content — produces a children's-book feel that undermines credibility.
- Using `blueprint` or `scientific` for narrative content — produces an instruction-manual feel that kills emotional engagement.
- Mixing more than one style in a single article — each illustration should be readable as part of the same set.
- Reaching for `pixel-art` or `vintage` without an in-content reason — these are register-defining choices; use them when the article is *about* games / history / the past, not for variety.
