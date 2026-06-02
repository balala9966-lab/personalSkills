# illustration-prompt-composer

The orchestration layer for adding illustrations to articles. Given an article and a style preset, it analyses content, plans illustration positions, composes prompts, dispatches generation through `illustration-image-backend`, and writes the resulting images back into the source document.

This skill does not generate images itself — that's `illustration-image-backend`'s job. It does not own style metadata — that's `illustration-styles`. Its responsibility is the *workflow*.

## Install

```bash
ln -s "$(pwd)/illustration-prompt-composer" ~/.claude/skills/illustration-prompt-composer
```

Also install the two dependencies:

```bash
ln -s "$(pwd)/illustration-styles" ~/.claude/skills/illustration-styles
ln -s "$(pwd)/illustration-image-backend" ~/.claude/skills/illustration-image-backend
```

Or, if you keep them in a different location:

```bash
export ILLUSTRATION_STYLES_HOME=/path/to/illustration-styles
export ILLUSTRATION_IMAGE_BACKEND_HOME=/path/to/illustration-image-backend
```

## Setup

```bash
# 1. Make illustration-image-backend usable (set credentials matching your backends.yaml)
export OPENAI_API_KEY=sk-...
mkdir -p ~/.config/illustration-image-backend
cp /path/to/illustration-image-backend/config/backends.example.yaml ~/.config/illustration-image-backend/backends.yaml

# 2. (Optional) Drop a preferences file to skip first-time questions
mkdir -p ~/.illustration-composer
cat > ~/.illustration-composer/EXTEND.md <<'YAML'
default_output_dir: imgs-subdir
default_backend: openai_images
default_style: editorial
preferred_palette: warm
language: en
density: per-section
YAML
```

## Use

### One-shot

```bash
python scripts/run.py /path/to/article.md --preset tech-explainer
```

### Step by step (recommended when iterating)

```bash
# Step 1+2: analyze the article and emit a skeleton outline
python scripts/analyze.py /path/to/article.md

# (note the workdir printed in stderr)

# Step 3+4: pick a preset/style/density and write the populated outline + initial mapping
python scripts/plan.py <workdir> --preset tech-explainer --density balanced

# Step 5: compose per-image prompt files
python scripts/compose.py <workdir>

# Step 6: dispatch the prompts to illustration-image-backend
python scripts/dispatch.py <workdir> --backend openai_images

# Step 7: write the images back into the source document
python scripts/writeback.py <workdir>
```

### Cover only

```bash
python scripts/run.py /path/to/article.md --mode cover --aspect 16:9 --style elegant --palette warm
```

### Both cover and body illustrations

```bash
python scripts/run.py /path/to/article.md --mode both --preset storytelling
```

### Public yuque (read-only writeback)

```bash
# Have Claude fetch the body first (or use the urllib fallback)
python scripts/run.py "https://www.yuque.com/foo/bar/baz" --preset knowledge-base
# Writeback step will print the markdown snippets for you to paste manually
```

## Layout

```
illustration-prompt-composer/
├── SKILL.md
├── README.md
├── references/
│   ├── workflow.md
│   ├── outline-schema.md
│   ├── mapping-schema.md
│   ├── prompt-templates.md
│   └── preferences-schema.md
├── scripts/
│   ├── util.py                 # path resolution, slugs, mapping IO
│   ├── preferences.py          # EXTEND.md loader
│   ├── styles_loader.py        # reads illustration-styles index
│   ├── analyze.py              # Step 1+2
│   ├── plan.py                 # Step 3+4
│   ├── compose.py              # Step 5
│   ├── dispatch.py             # Step 6
│   ├── writeback.py            # Step 7
│   └── run.py                  # one-shot wrapper
├── adapters/
│   ├── ingest/
│   │   ├── markdown.py
│   │   ├── text.py
│   │   ├── yuque_public.py
│   │   └── yuque_internal.py
│   ├── ingest_dispatcher.py
│   └── writeback/
│       ├── markdown.py
│       ├── yuque_internal.py
│       └── manual.py
└── examples/                   # fixtures for E2E testing
    ├── tech-prd.md
    ├── narrative-blog.md
    └── data-weekly.md
```

## What's Out Of Scope

- `.docx` and PDF inputs — convert to markdown first
- Image post-processing (upscale, crop, watermark overlay) — use a separate tool
- Iterative image refinement UI — re-run `dispatch.py` with edited prompts
- Direct CDN upload — relies on whatever URLs the backend returns

## Dependencies

- Python 3.9+ standard library
- `illustration-styles` skill (knowledge base)
- `illustration-image-backend` skill (image generation dispatcher)
- Optional: PyYAML (we fall back to a tiny YAML parser if it's missing)
- For yuque writeback: the `yuque-mcp` MCP server connected to your Claude session
