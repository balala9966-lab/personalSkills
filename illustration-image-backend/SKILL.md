---
name: illustration-image-backend
description: Unified pluggable image-generation dispatcher. Routes a normalized request to one of several backends (OpenAI Images, OpenAI-compatible proxies like Azure/OpenRouter, Google Gemini Imagen, or an optional local CLI). Use this skill when you need to generate an image from a prompt and want backend choice to be configurable instead of hard-coded. Triggers on phrases like "generate image", "render image", "出图", "生成图片", "调出图后端", "image API", "OpenAI Images", "Imagen", "switch image backend".
---

# illustration-image-backend

A pluggable dispatcher for image generation. Composer skills (and humans) call one CLI, and a YAML config decides which backend actually executes the request.

## Why It Exists

Prompt-composing skills should not know whether the image will be rendered by OpenAI, Gemini, an internal CLI, or a local SD instance. This skill hides that choice behind a single CLI + a config file.

## Backends Shipped

| Backend | Type id | Auth | Network | Refs/img2img |
|---------|---------|------|---------|--------------|
| OpenAI Images | `openai_images` | `OPENAI_API_KEY` | public | not supported via `/images/generations` |
| OpenAI-compatible proxy | `openai_compat` | any header/query | configurable | same as above |
| Google Gemini Imagen | `gemini_imagen` | `GEMINI_API_KEY` + `google-generativeai` pip pkg | public | not supported |

List the backends actually registered in your install:

```bash
python scripts/generate.py --list-backends
```

## Quick Start

### 1. Configure

Copy the example and fill in API keys via env vars:

```bash
mkdir -p ~/.config/illustration-image-backend
cp config/backends.example.yaml ~/.config/illustration-image-backend/backends.yaml
$EDITOR ~/.config/illustration-image-backend/backends.yaml
export OPENAI_API_KEY=sk-...
```

Config search order: `--config` arg → `$ILLUSTRATION_IMAGE_BACKEND_CONFIG` → `./illustration-image-backend.yaml` → `~/.config/illustration-image-backend/backends.yaml` → `~/.illustration-image-backend/backends.yaml`.

### 2. Generate

Inline:

```bash
python scripts/generate.py \
  --prompt "A minimal hand-drawn editorial illustration, 16:9, pure white background" \
  --backend openai_images \
  --width 1536 --height 1024 \
  --output-dir ~/Pictures/ai \
  --out-json /tmp/result.json
```

Or pass a request file (preferred when the prompt is long or has reference images):

```bash
python scripts/generate.py --request /tmp/request.json --out-json /tmp/result.json
```

Where `/tmp/request.json` is a serialized `GenerateRequest` — see `references/adapter-spec.md`.

### 3. Use Model Aliases

When you want to use a model alias without specifying the full backend+model:

```bash
python scripts/generate.py --alias banana --prompt "..."
```

Aliases live under `aliases:` in the YAML config.

## Output Contract

- **stdout**: one absolute PNG path per generated image, one per line. Pipe-friendly.
- **stderr**: progress and errors.
- **`--out-json`**: full `GenerateResponse` JSON — the preferred way for other skills to consume the result.

Exit codes: `0` success / `1` argument or config error / `2` backend error / `3` unexpected exception.

## When To Use This Skill

- Another skill (e.g. `illustration-prompt-composer`) needs to render a prompt and wants backend choice deferred.
- The user wants to try the same prompt across multiple backends.
- The user wants to keep credentials and endpoint URLs in one config file instead of scattering them across many skills.

## When NOT To Use This Skill

- You just want one ad-hoc image and don't mind hard-coding the call — the standalone `generate-image-public` script in this repo is simpler.
- You need a feature one specific backend has (e.g. Gemini's negative prompt control) — go direct.

## Extending With A New Backend

1. Create `adapters/<my_backend>.py`.
2. Subclass `ImageBackend` from `base.py`. Implement `name`, `capabilities`, `generate(req)`, and (when relevant) `available()`.
3. Call `register("<type-id>", MyBackend)` at module bottom.
4. The CLI auto-loads every `adapters/*.py`, so no manual wiring is needed.
5. Add a sample stanza under `backends:` in `config/backends.example.yaml`.

Full spec: `references/adapter-spec.md`.

## Programmatic Use

```python
import sys; sys.path += ["/path/to/illustration-image-backend/scripts", "/path/to/illustration-image-backend/adapters"]
import base, registry
import openai_images, openai_compat, gemini_imagen  # registers them

req = base.GenerateRequest(prompt="...", width=1536, height=1024)
backend = registry.get_backend("openai_images", {"api_key_env": "OPENAI_API_KEY"})
resp = backend.generate(req)
for img in resp.images:
    print(img.path)
```
