# Preferences Schema (EXTEND.md)

User-level preferences for the composer. Reduces the number of questions in Step 3 by remembering past choices.

## Location

Search order (first found wins):

1. `./.illustration-composer/EXTEND.md` (project-local — for repos that want a shared illustration style)
2. `$XDG_CONFIG_HOME/illustration-composer/EXTEND.md` (or `$HOME/.config/illustration-composer/EXTEND.md`)
3. `$HOME/.illustration-composer/EXTEND.md` (user-level default)

If none found, Step 1 of the workflow runs first-time setup and writes one.

## Format

YAML, top-level mapping. Unknown keys are ignored (forward-compatible).

```yaml
default_output_dir: imgs-subdir
default_backend: openai_images
default_model: gpt-image-1
default_style: editorial
default_type: infographic
preferred_palette: warm
language: en
density: per-section
mode: illustration
watermark:
  enabled: false
  content: ""
  position: bottom-right
```

## Field Reference

### Output location

| Field | Allowed values | Effect |
|-------|---------------|--------|
| `default_output_dir` | `imgs-subdir` (default) / `same-dir` / `illustrations-subdir` / `independent` | Determines where the article-slug working directory lives. See `workflow.md`. |

### Backend defaults

| Field | Effect |
|-------|--------|
| `default_backend` | Backend name (matches a key in `illustration-image-backend/backends.yaml`). Used when neither the request nor `outline.md` overrides. |
| `default_model` | Model id. Overrides the backend's own default. |

### Style defaults

| Field | Effect |
|-------|--------|
| `default_style` | Style id (matches one in `illustration-styles/references/styles.md`). Used as Q3 default in Step 3. |
| `default_type` | Type id. Used as Q1 default if no preset is selected. |
| `preferred_palette` | Palette id. Used when the chosen style has no canonical palette pairing forced. |
| `density` | `minimal` / `balanced` / `per-section` / `rich`. Used as Q2 default in Step 3. |
| `mode` | `illustration` / `cover` / `both`. Default mode for one-shot invocations. |

### Image labels

| Field | Effect |
|-------|--------|
| `language` | Default label language. Overridden by detected article language unless you set `lock_language: true`. |
| `lock_language` | If true, always use `language` even when article is in a different language. |

### Watermark

| Field | Effect |
|-------|--------|
| `watermark.enabled` | When true, the composer appends a watermark instruction to every prompt. |
| `watermark.content` | The actual watermark text. |
| `watermark.position` | `top-left` / `top-right` / `bottom-left` / `bottom-right`. |

## Precedence

When generating an image, the resolved value comes from (highest priority first):

1. CLI argument to the script
2. `outline.md` frontmatter
3. Active illustration block's local field
4. `EXTEND.md` field
5. Hard-coded default in code

This means the user can override at any layer without editing earlier artifacts.

## First-Time Setup

When no `EXTEND.md` is found, Step 1 runs an interactive setup:

1. Where should image files live? (4 options matching `default_output_dir`)
2. Which backend should be the default? (lists registered backends from `illustration-image-backend`)
3. Preferred default style? (offers 5-6 popular options + "decide per article")
4. Default label language? (en / zh / decide per article)

Writes the answers to `$HOME/.illustration-composer/EXTEND.md` and continues.
