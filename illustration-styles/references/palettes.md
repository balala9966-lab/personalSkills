# Palettes

11 color palettes. Each palette is a *discipline*, not just a hue picker — it tells the generator what colors to use *and* how to use them (semantic role for each color, base background, accent rules).

## Body illustration palettes

| Palette | Description | Best for |
|---------|-------------|----------|
| `macaron` | Soft macaron tones (blue, mint, lavender, peach) on warm cream | Education, knowledge sharing, tutorials |
| `warm` | Warm earth tones (orange, terracotta, gold) on soft peach, no cool colors | Brand, lifestyle, products |
| `neon` | Vivid neons (pink, cyan, yellow) on deep purple | Gaming, retro, pop culture |
| `mono-ink` | Pure white with black ink, sparse semantic accents (coral, teal, lavender) | Visual notes, manifestos, comparison pieces |

## Cover palettes

| Palette | Description | Best for |
|---------|-------------|----------|
| `warm` | Warm orange / terracotta / gold | Lifestyle, human-interest, emotional |
| `elegant` | Refined gold / deep green / cream | Business, thought leadership |
| `cool` | Cool blue / cyan / silver-white | Tech, AI, engineering |
| `dark` | Dark backgrounds, high contrast | Deep-tech articles, "dark mode" aesthetic |
| `earth` | Earth brown / olive / cream | Nature, sustainability, humanities |
| `vivid` | High-saturation clashing color | Fashion, creative, internet culture |
| `pastel` | Soft pastels | Light content, illustrative |
| `mono` | Black / white / gray monochrome | Minimal, academic, formal |
| `retro` | Retro brown / orange / paper texture | Nostalgia, brand storytelling |
| `duotone` | Two-color high-tension | Posters, visual punch |
| `macaron` | Macaron softness | Educational covers |

## Auto-Pick Rules

| Content signal | Recommended palette |
|----------------|--------------------|
| Tech, AI, programming | `cool` or `dark` |
| Business, strategy | `elegant` |
| Education, tutorial | `macaron` |
| Lifestyle, emotion | `warm` |
| Nature, sustainability | `earth` |
| Opinion, commentary | `duotone` or `vivid` |
| Visual notes / comparisons | `mono-ink` |
| Default fallback for body illustrations | `macaron` |
| Default fallback for covers | `elegant` |

## How A Palette Combines With A Style

The palette adjusts the style's color slot, not its line work or composition. For example:

- `editorial` style + `warm` palette = magazine infographic with orange-terracotta accents
- `editorial` style + `cool` palette = same magazine infographic but with cool blues
- `notion` style + `macaron` palette = the canonical educational-Notion look
- `screen-print` style + `duotone` palette = high-contrast op-ed poster

Some style+palette combos fight each other (e.g. `pixel-art` + `pastel` looks washed out, `blueprint` + `warm` looks confused). When unsure, default to the palette the style was originally designed for; see the per-style detail pages for canonical pairings.
