# Workflow

Detailed 7-step process for adding illustrations to an article. Each step has a script (`scripts/<step>.py`) and emits files to disk so you can inspect / edit between steps.

## File Layout Produced

```
{output_root}/{article_slug}/
├── outline.md            # Step 4 — planning document
├── .mapping.json         # Step 6 — image registry, updated as generation completes
├── references/           # Step 1 — user-supplied reference images (if any)
│   ├── 01-ref-{slug}.png
│   └── 01-ref-{slug}.md  # description / usage hint
├── prompts/              # Step 5 — one prompt file per planned image
│   └── NN-{type}-{slug}.md
└── NN-{type}-{slug}.png  # Step 6 — final image files
```

`{output_root}` is determined by `EXTEND.md`'s `default_output_dir`:

| `default_output_dir` | `{output_root}` |
|---------------------|-----------------|
| `imgs-subdir` (default) | `{article-dir}/imgs/` |
| `same-dir` | `{article-dir}/` |
| `illustrations-subdir` | `{article-dir}/illustrations/` |
| `independent` | `illustrations/` relative to cwd (use for pasted content with no source file) |

`{article_slug}` is the source filename (without extension) for markdown sources, or a generated slug for pasted text / URL sources.

## Step 1 — Ingest & Preflight

### 1.1 Pick ingest adapter

Detect source type from the input string:
- Starts with `http://` or `https://`, host = `*.yuque.com` → `yuque_public`
- Path ends with `.md` and file exists → `markdown`
- Anything else → `text` (treats as plain text, stdin-friendly)

### 1.2 Load preferences (EXTEND.md)

Search order (first match wins):
1. `./.illustration-composer/EXTEND.md`
2. `$XDG_CONFIG_HOME/illustration-composer/EXTEND.md` (or `$HOME/.config/...`)
3. `$HOME/.illustration-composer/EXTEND.md`

If none found, run first-time setup: prompt for output dir convention, default backend, default style, label language. Write to `$HOME/.illustration-composer/EXTEND.md`.

### 1.3 Save user reference images

If the user provided reference images (file paths in the request, or attached in the conversation):
- Copy each to `{output_root}/{slug}/references/NN-ref-{slug}.png`
- Write a sidecar `NN-ref-{slug}.md` with one-line description
- Record paths for use in Step 5

If the user described reference style verbally (no files), extract style/palette keywords into `extracted-style.md` for use in the prompt body. Do not add to `references` frontmatter.

## Step 2 — Analyze

Read the ingested content. Detect:

| Dimension | Output |
|-----------|--------|
| `content_type` | technical / tutorial / methodology / narrative / opinion / data / comparison / history / academic / saas / unknown |
| `core_claims` | 2-5 main arguments worth visualizing |
| `cognitive_anchors` | sections that would benefit from an illustration: the main claim, breakpoints, before/after, branching, common traps |
| `image_positions` | provisional list of paragraph anchors where images go |
| `recommended_preset` | from `illustration-styles/references/auto-recommend.md` |
| `recommended_density` | minimal/balanced/per-section/rich based on word count |
| `article_language` | detected language for labels |

**Critical**: when the article uses a metaphor (e.g. "splitting a watermelon with a chainsaw"), illustrate the *underlying concept*, not the literal phrase.

## Step 3 — Confirm

Single `AskUserQuestion` call with up to 4 questions. Skip Qs whose answer was already specified in the user's request or is unambiguous from preferences.

### Q1 (always required when not pre-specified): preset or type

Recommend the preset from Step 2's `recommended_preset`. Offer 1-2 alternates plus a manual-type-pick option.

### Q2 (always required when not pre-specified): density

minimal (1-2) / balanced (3-5) / per-section (recommended for long articles) / rich (6+).

### Q3 (skip when a preset was picked in Q1): style

If `EXTEND.md` has `preferred_style`, recommend it first. Otherwise offer 2-3 styles strongly compatible with the chosen Type.

### Q4 (only when language is ambiguous): label language

Skip if article language matches `EXTEND.md.language`.

## Step 4 — Outline

Write `{output_root}/{slug}/outline.md`:

```yaml
---
article_slug: <slug>
type: <type-id>
style: <style-id>
palette: <palette-id>
density: <density>
image_count: <N>
mode: illustration|cover|both
references:                    # only if real files exist in references/
  - ref_id: 01
    filename: 01-ref-brand.png
    description: brand color reference
---

## Illustration 1

**Position**: <section name> / <paragraph snippet>

**Purpose**: <why an image here helps the reader>

**Visual Content**:
- <element 1>
- <element 2>
- <element 3>

**Type Application**: <how this Type expresses the concept>

**References**: [01]          # optional

**Reference Usage**: direct    # direct | style | palette

**Filename**: 01-<type>-<slug>.png

## Illustration 2
...
```

For `cover` mode, produce a single `## Cover` block. For `both`, the cover block first.

## Step 5 — Compose prompts (BLOCKING)

For each block in `outline.md`, write `{output_root}/{slug}/prompts/NN-{type}-{slug}.md`.

### Frontmatter

```yaml
---
illustration_id: 01
type: <type-id>
style: <style-id>
palette: <palette-id>
aspect: 16:9
references: [01]      # only if real files exist
---
```

### Body

The full prompt sent to the image backend. Use `references/prompt-templates.md` for type-specific skeletons. Required slots:

- **Layout**: overall composition (grid / radial / hierarchy / left-right / top-bottom)
- **Zone breakdown**: what's in each visual region
- **Labels**: use specific terms/numbers from the article, not generic placeholders
- **Color**: hex codes with semantic meaning (e.g. `coral red (#E07A5F) for emphasis`)
- **Style**: line treatment, texture, mood, character rendering
- **Aspect**: width:height ratio

Do not generate any image until *every* prompt file is on disk. Validation step:

```
Prompt files:
- prompts/01-infographic-overview.md ✓
- prompts/02-infographic-pitfalls.md ✓
- ...
```

Backup rule: if a prompt file already exists, rename it to `NN-{type}-{slug}-backup-YYYYMMDD-HHMMSS.md` before writing the new one.

## Step 6 — Dispatch

For each prompt file:

1. Read the prompt frontmatter and body.
2. Resolve refs (only if the role is `direct` and the backend's capabilities include `refs_direct`).
3. Build a `GenerateRequest` JSON and write to a temp file.
4. Invoke `illustration-image-backend/scripts/generate.py --request <tmp> --out-json <result>`.
5. Parse the result. On success, update `.mapping.json` with the new entry.
6. On failure: retry once. If still failing, record the error in `.mapping.json` under the entry's `error` field and continue to the next image.

`.mapping.json` schema is in `references/mapping-schema.md`.

## Step 7 — Writeback

Pick writeback adapter based on the ingest source type:

| Ingest source | Writeback adapter | Behavior |
|---------------|------------------|----------|
| `markdown` | `markdown` | Direct file edit; inserts `![alt](relative/path.png)` after the target paragraph |
| `yuque_internal` | `yuque_internal` | Calls `skylark_doc_update` via MCP with patched markdown |
| `yuque_public` | `yuque_public` | Prints the markdown snippets the user should paste manually |
| `text` | `text` | Prints the markdown snippets; nothing to write back to |

### Markdown insertion convention

Insert one blank line, the image syntax, a blank line, after the paragraph that matches the `Position` field. Alt text uses the article's language (matches `outline.md`'s `language` setting).

Relative path is computed from the `default_output_dir` setting — see the layout table at the top of this file.

### Yuque-internal writeback

For images that have a `remote_url` (provided by the backend), substitute the local path in the markdown with the remote URL before calling `skylark_doc_update`. This way the target platform can render the images directly from the URL without a separate upload step.

For images without a `remote_url` (e.g. generated by OpenAI), the writeback adapter must skip yuque-internal writeback for those images and surface a clear warning — yuque cannot reach local file paths.

## Failure Modes

| Step | Failure | Recovery |
|------|---------|----------|
| 1 | Ingest adapter cannot read source | Stop. Tell user the specific reason (file missing, URL 401, etc.). |
| 1 | EXTEND.md missing | Run first-time setup (single AskUserQuestion). |
| 3 | User cancels confirmation | Stop. Preserve any artifacts already written. |
| 5 | Cannot write prompt files (disk full, permissions) | Stop. Do not proceed to Step 6. |
| 6 | One backend call fails | Retry once. On second failure, log and continue. Other images still generate. |
| 7 | Writeback adapter cannot write | Print the markdown snippets so the user can paste manually. Do not crash. |
