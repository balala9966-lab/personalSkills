# illustration-image-backend

A pluggable image-generation dispatcher. One CLI, one YAML config, multiple backends behind a uniform interface.

## Install

```bash
ln -s "$(pwd)/illustration-image-backend" ~/.claude/skills/illustration-image-backend
```

## Setup

```bash
mkdir -p ~/.config/illustration-image-backend
cp config/backends.example.yaml ~/.config/illustration-image-backend/backends.yaml
$EDITOR ~/.config/illustration-image-backend/backends.yaml

# Set credentials your config references:
export OPENAI_API_KEY=sk-...
# Optional:
export GEMINI_API_KEY=...
```

Optional pip packages:

```bash
pip install google-generativeai   # only needed for gemini_imagen backend
pip install pyyaml                # not required — we ship a tiny YAML subset parser
```

## Use

```bash
# Default backend from config:
python scripts/generate.py --prompt "..."

# Specific backend:
python scripts/generate.py --backend openai_images --prompt "..."

# Via model alias:
python scripts/generate.py --alias gpt-image --prompt "..."

# From a request file:
python scripts/generate.py --request /tmp/req.json --out-json /tmp/result.json
```

## Layout

```
illustration-image-backend/
├── SKILL.md
├── README.md
├── scripts/
│   ├── base.py         # ABC + GenerateRequest/Response dataclasses
│   ├── registry.py     # backend type registry
│   ├── config.py       # YAML loader (uses PyYAML if installed, else tiny parser)
│   └── generate.py     # CLI entrypoint
├── adapters/
│   ├── openai_images.py
│   ├── openai_compat.py
│   └── gemini_imagen.py
├── config/
│   └── backends.example.yaml
└── references/
    ├── adapter-spec.md
    ├── config-schema.md
    └── error-codes.md
```

## Backends At A Glance

| Type | Network | Key env | Pip dep | Refs |
|------|---------|---------|---------|------|
| `openai_images` | public | `OPENAI_API_KEY` | none | no |
| `openai_compat` | configurable | configurable | none | no |
| `gemini_imagen` | public | `GEMINI_API_KEY` | `google-generativeai` | no |

## Why Three Adapters For OpenAI-Family?

- `openai_images` — talks to `api.openai.com` directly. The common case.
- `openai_compat` — same wire protocol but pointed at an OpenAI-compatible host (Azure, OpenRouter, LiteLLM, internal proxies). Lets you have *multiple* backends in your config that all speak OpenAI's protocol but route differently.
- They share code: `openai_compat` is a thin subclass.
