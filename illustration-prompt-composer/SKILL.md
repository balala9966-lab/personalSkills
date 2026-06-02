---
name: illustration-prompt-composer
description: Orchestration skill for adding illustrations to articles. Reads the article (markdown, public yuque URL, internal yuque URL, or plain text), identifies where illustrations would help, picks Type/Style/Palette via the `illustration-styles` knowledge base, composes prompts, dispatches generation through `illustration-image-backend`, and writes the resulting images back into the original article. Triggers on phrases like "配图", "插图", "封面", "为文章配图", "给这篇文章生成插图", "article illustration", "cover image", "shot list", "give this article some images". Supports illustration mode (multiple body images), cover mode (one cover image), and both. Default to English-language image labels unless the article is in another language.
---

# illustration-prompt-composer

The orchestration layer: takes an article, decides where images go, what they should look like, how to prompt for them, and where the resulting files land in the source document.

This skill does not generate images itself — it delegates that to `illustration-image-backend`. It does not own style knowledge — it queries `illustration-styles`. Its job is the *workflow*: ingest → analyze → confirm → outline → compose prompts → dispatch → write back.

## Dependencies

This skill assumes both of these are installed and discoverable:

- **`illustration-styles`** (sibling skill or env var `ILLUSTRATION_STYLES_HOME`) — for Type/Style/Palette/preset definitions
- **`illustration-image-backend`** (sibling skill or env var `ILLUSTRATION_IMAGE_BACKEND_HOME`) — for the actual image generation

If either is missing, the relevant step surfaces a clear error and stops.

## Supported Inputs

| Input | Adapter | Notes |
|-------|---------|-------|
| Local markdown file (`.md`) | `markdown` | Default; supports both inline images and pasted-content mode |
| Public yuque URL (`yuque.com/...`) | `yuque_public` | Read-only — writeback prompts user to copy manually |
| Plain text (stdin or `.txt` file) | `text` | No writeback (no original document to update) |

`.docx` and PDF inputs are deliberately not supported — convert to markdown first.

## Modes

| Mode | What you get |
|------|-------------|
| `illustration` | A shot list, then N body illustrations placed inside the article |
| `cover` | A single cover image |
| `both` | Cover + body illustrations |

If the user does not specify a mode in the request, ask via `AskUserQuestion` in Step 3.

## Workflow

Detailed steps in `references/workflow.md`. Summary:

1. **Ingest & preflight** — Pick the ingest adapter for the source. Load the article into a normalized form. Load user preferences from `EXTEND.md` if present; if not, run first-time setup.
2. **Analyze** — Identify content type (technical / tutorial / narrative / opinion / ...), candidate illustration positions, and any user-supplied reference images.
3. **Confirm** — Single `AskUserQuestion` collecting Q1 preset/type, Q2 density, Q3 style (skipped if a preset was picked), Q4 label language (only when ambiguous).
4. **Outline** — Write `{output_dir}/{slug}/outline.md` with one block per illustration: Position / Purpose / Visual content / Filename.
5. **Compose prompts** — One `{output_dir}/{slug}/prompts/NN-{type}-{slug}.md` per illustration, with YAML frontmatter (type/style/palette/refs) and the full prompt body. **Blocking**: every prompt file must be on disk before any image is generated.
6. **Dispatch** — Loop over the prompt files, calling `illustration-image-backend/scripts/generate.py`. Update `{output_dir}/{slug}/.mapping.json` after each success with localPath, remote_url, model, seed.
7. **Writeback** — Use the matching writeback adapter to insert `![alt](relative/path.png)` into the original document at the planned position. For non-writable sources (`yuque_public`, `text`), print the markdown snippets and ask the user to paste them manually.

## Quick Start

```bash
# End-to-end on a local markdown file:
python scripts/run.py /path/to/article.md --preset tech-explainer

# Step by step (when you want to inspect/edit intermediate artifacts):
python scripts/analyze.py /path/to/article.md
python scripts/plan.py /path/to/article.md/imgs/article/outline.md --preset tech-explainer
python scripts/compose.py /path/to/article.md/imgs/article/.mapping.json
python scripts/dispatch.py /path/to/article.md/imgs/article/.mapping.json
python scripts/writeback.py /path/to/article.md /path/to/article.md/imgs/article/.mapping.json

# Cover only:
python scripts/run.py /path/to/article.md --mode cover --aspect 16:9

# From a yuque public URL:
python scripts/run.py "https://www.yuque.com/foo/bar/baz" --preset storytelling
```

## Preferences (EXTEND.md)

A small YAML file controlling defaults. Search order: project-local
`.illustration-composer/EXTEND.md` → `$XDG_CONFIG_HOME/illustration-composer/EXTEND.md` → `~/.illustration-composer/EXTEND.md`.

```yaml
default_output_dir: imgs-subdir   # imgs-subdir | same-dir | illustrations-subdir | independent
default_backend: openai_images
default_model: gpt-image-1
default_style: editorial
preferred_palette: warm
language: en                       # default label language; overridden by article-language detection
density: per-section
watermark: { enabled: false, content: "", position: "bottom-right" }
```

See `references/preferences-schema.md` for field details and `references/workflow.md` Step 1 for the first-time setup.

## What This Skill Deliberately Doesn't Do

- Doesn't render images (use `illustration-image-backend`).
- Doesn't define style metadata (use `illustration-styles`).
- Doesn't handle `.docx` or PDF inputs — convert first.
- Doesn't upload images to remote CDNs — output is local paths. Writeback to yuque transparently uses whatever URLs `illustration-image-backend` returned in `remote_url`, but does not arrange storage itself.
- Doesn't iterate generations automatically — if a result is unsatisfactory, re-run `dispatch.py` with edited prompts.
