---
name: generate-image-public
description: Generate images via OpenAI's public Images API (gpt-image-1). Use this skill when the user asks to create, generate, draw, or render an image and wants a public-internet image-generation backend (no internal company gateway). Triggers on phrases like "generate an image", "create an illustration", "render this prompt", "draw a picture", "出图", "生成图片", "画一张". Pairs naturally with editorial-illustration or any other skill that produces image prompts.
---

# Generate Image (Public)

Calls the public OpenAI Images API to turn a text prompt into a PNG file on disk. No company gateway, no internal credentials — only an `OPENAI_API_KEY`.

This skill is the runtime counterpart to skills that *compose* image prompts (such as `editorial-illustration`). When such a skill produces a prompt and the user asks for the rendered image, invoke this skill with the prompt.

## When To Use

- User asks to generate / create / draw / render an image and you have, or can compose, a prompt.
- A sibling skill produces a prompt and the user wants the image rendered without leaving the chat.
- The user explicitly wants a non-company image backend (private repo, personal Mac, off-network use).

## Prerequisites

- Python 3.9+ (uses only the standard library — no `pip install` required).
- An OpenAI API key with access to `gpt-image-1`, exposed as `OPENAI_API_KEY` (or passed via `--token`).
- Optional: `OPENAI_BASE_URL` if the user routes through an OpenAI-compatible proxy (Azure, OpenRouter, local LiteLLM).

## How To Invoke

The script lives at `scripts/generate_image.py` relative to this SKILL.md. Always pass `--prompt`. Print the prompt back to the user before running so they can copy it elsewhere if rendering fails.

```bash
python3 scripts/generate_image.py \
  --prompt "<full prompt text>" \
  --size 1536x1024 \
  --output-dir <where-to-save>
```

### Recommended defaults

| Use case | Size | Quality |
|----------|------|---------|
| Editorial body illustration (16:9) | `1536x1024` | `high` |
| Vertical / story format (9:16) | `1024x1536` | `high` |
| Square avatar / icon | `1024x1024` | `medium` |
| Quick draft | any | `low` |

### Arguments

| Flag | Required | Default | Notes |
|------|----------|---------|-------|
| `--prompt`, `-p` | yes | — | Full prompt text. Quote it carefully if it contains newlines. |
| `--token` | no | `$OPENAI_API_KEY` | Override only when scripting with multiple keys. |
| `--base-url` | no | `$OPENAI_BASE_URL` or `https://api.openai.com/v1` | OpenAI-compatible endpoint. |
| `--model`, `-m` | no | `$OPENAI_IMAGE_MODEL` or `gpt-image-1` | Use `gpt-image-1` for the editorial style. |
| `--size` | no | `1536x1024` | `gpt-image-1` supports 1536x1024 / 1024x1536 / 1024x1024 / `auto`. |
| `--quality` | no | `high` | `low` / `medium` / `high` / `auto`. |
| `-n`, `--count` | no | `1` | Generate multiple variants in one call. |
| `--output-dir`, `-o` | no | `$IMAGE_OUTPUT_DIR` or `.image_process` | Files saved as `<model>_<yyyymmddHHMMSS>_<N>.png`. |

### Output contract

- **stdout**: one absolute file path per generated image, one per line. Capture this for downstream use.
- **stderr**: progress messages and errors.
- **exit code**: `0` success / `1` arg or config error / `2` API or network error / `3` unexpected error.

## Workflow For The Agent

1. Confirm or compose the prompt. If a sibling skill (e.g. `editorial-illustration`) already produced one, use it verbatim.
2. Echo the prompt to the user in a fenced code block so they can keep a copy.
3. Decide size from the user's intent (article body → `1536x1024`).
4. Run the script. If it exits non-zero, surface the stderr message; do not silently retry with a different prompt.
5. After success, give the user the saved path and a one-line note on what they should sanity-check (whitespace, character silhouette, text legibility).
6. For revisions: compose a revised prompt and call the script again with a new output filename. Do not edit the previous PNG in place.

## Troubleshooting

- **`error: missing OpenAI API key`** — Set `OPENAI_API_KEY` in the shell, or pass `--token`. The skill never reads from any company gateway.
- **`HTTP 401`** — Key invalid or revoked. Regenerate at https://platform.openai.com/api-keys.
- **`HTTP 400 / invalid size`** — `gpt-image-1` only accepts the sizes listed above; older endpoints like `dall-e-3` accept different sizes.
- **`HTTP 429`** — Rate-limited or quota exhausted. Wait or check billing.
- **Network failure** — If on a corporate network, you may need to set `HTTPS_PROXY` or use `--base-url` to point at an internal proxy.

## What This Skill Deliberately Does Not Do

- Does not call any internal company API.
- Does not store credentials. The key lives in the user's environment only.
- Does not compose prompts. Prompt-shaping belongs to skills like `editorial-illustration`.
- Does not post-process images (no upscaling, cropping, watermarking). Use a separate tool for that.
