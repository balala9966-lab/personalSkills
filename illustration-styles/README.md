# illustration-styles

Pure knowledge base of illustration metadata: 6 Types × 23 Styles × 11 Palettes × 19 Presets, plus the Type × Style compatibility matrix and content-type → preset recommendation rules.

Designed to be **read** by other illustration skills (or humans), not invoked directly.

## Install

```bash
ln -s "$(pwd)/illustration-styles" ~/.claude/skills/illustration-styles
```

Optionally export `ILLUSTRATION_STYLES_HOME` to point at the install location so composer skills can find it.

## Layout

```
illustration-styles/
├── SKILL.md
├── README.md
├── references/
│   ├── types.md            # the 6 Types
│   ├── styles.md           # the 23 Styles, grouped by family
│   ├── palettes.md         # the 11 Palettes
│   ├── presets.md          # the 19 Presets
│   ├── compatibility.md    # Type × Style matrix
│   ├── auto-recommend.md   # content type → preset rules
│   └── index.json          # machine-readable index
├── styles/                 # one .md per Style
├── palettes/               # one .md per Palette
└── presets/                # one .md per Preset
```

## Why It's Separate

The four original illustration skills duplicated their style lists. Splitting the knowledge into a standalone skill means:

- Adding a new style happens in one place.
- Compatibility ratings stay consistent across all composer skills.
- Composer skills can stay focused on *workflow*, not *style data*.

## Origins

Style and palette taxonomies originate from prior internal illustration workflows. Specific brand-tied names, internal product references, and CLI binding details have been removed; the taxonomy itself is general-purpose visual-design knowledge.
