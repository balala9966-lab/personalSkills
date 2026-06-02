# generate-image-public

A Claude Code skill that renders an image prompt to a PNG file using the **public OpenAI Images API** (`gpt-image-1`). No company gateway, no internal credentials.

Designed as the runtime backend for prompt-composing skills like `editorial-illustration`, but works standalone with any prompt.

## Install

```bash
ln -s "$(pwd)/generate-image-public" ~/.claude/skills/generate-image-public
```

## Setup

```bash
export OPENAI_API_KEY=sk-...   # required
export OPENAI_BASE_URL=https://api.openai.com/v1   # optional, for proxies
export IMAGE_OUTPUT_DIR=~/Pictures/ai-generated     # optional, default .image_process
```

## Use From The Shell

```bash
python3 scripts/generate_image.py \
  --prompt "A minimal hand-drawn editorial illustration of a tinkerer balancing two scales on a pure white background, 16:9, thin black lines" \
  --size 1536x1024 \
  --output-dir ~/Pictures/ai-generated
```

Stdout prints the absolute path of each saved PNG.

## Use From Claude Code

Just ask. Examples:

- "Render this prompt as an image."
- "Generate an image for the illustration prompt you just wrote."
- "出图。"

If you have both `editorial-illustration` and this skill installed, the editorial skill will compose the prompt and hand it to this skill for rendering.

## Why A Separate Skill For This?

This skill exists so:

- The personal-repo workflow works off any corporate network — only `OPENAI_API_KEY` is required.
- The skill can be shared publicly without leaking internal endpoints or credentials.
- Users can swap to any OpenAI-compatible backend (Azure / OpenRouter / local LiteLLM) via `OPENAI_BASE_URL`.
- Prompt composition (e.g. `editorial-illustration`) and image rendering stay decoupled — swap either side independently.

## Dependencies

Zero `pip install` requirements. Uses only Python 3.9+ standard library (`urllib`, `base64`, `json`).
