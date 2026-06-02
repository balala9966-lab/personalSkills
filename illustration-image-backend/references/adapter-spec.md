# Adapter Spec

How to write a new illustration-image-backend adapter.

## Minimum Implementation

```python
# adapters/my_backend.py

from base import (
    GenerateRequest, GenerateResponse, ImageBackend, ImageOut, ErrorInfo,
)
from registry import register


class MyBackend(ImageBackend):
    name = "my_backend"
    capabilities = {
        "max_n": 1,
        "refs_direct": False,
        "refs_style": False,
        "refs_palette": False,
        "negative_prompt": False,
        "seed": False,
        "sizes": ["1024x1024"],
    }

    def __init__(self, config: dict):
        super().__init__(config)
        # parse config fields here

    def available(self) -> tuple[bool, str]:
        # Return (False, "reason") if the backend cannot run.
        # Examples: missing API key, missing optional pip package, missing CLI binary.
        return True, ""

    def generate(self, req: GenerateRequest) -> GenerateResponse:
        # 1. Check available()
        # 2. Build the HTTP/CLI/SDK call
        # 3. Save resulting bytes to req.output_dir
        # 4. Return GenerateResponse with images=[ImageOut(...)]
        ...


register("my_backend", MyBackend)
```

The CLI auto-imports every `.py` file in `adapters/` at startup, so no manual wiring needed.

## GenerateRequest Fields

| Field | Type | Notes |
|-------|------|-------|
| `prompt` | str | The composed image-generation prompt. |
| `negative_prompt` | str \| None | Some backends (Gemini, SD) support; OpenAI Images does not. |
| `width` | int | Canvas width in pixels. |
| `height` | int | Canvas height in pixels. |
| `n` | int | Number of variants in one call. Default 1. |
| `seed` | int \| None | Where supported. |
| `refs` | list[Reference] | Reference images. Each has `path`, `role` (direct/style/palette), `weight`. |
| `output_dir` | str | Where to save PNGs. Adapter must `mkdir -p`. |
| `filename` | str \| None | Honored when `n==1`; otherwise adapters auto-generate names. |
| `model` | str \| None | Override the backend's default model. |
| `extra` | dict | Backend-specific knobs (e.g. `quality` for OpenAI). |

## GenerateResponse Fields

| Field | Type | Notes |
|-------|------|-------|
| `ok` | bool | True iff at least one image was saved. |
| `backend` | str | Adapter's `name` attribute. |
| `model` | str | Resolved model (after `req.model` fallback). |
| `elapsed_ms` | int | Wall-clock duration. |
| `images` | list[ImageOut] | One entry per generated file. |
| `raw` | dict | Adapter's raw upstream response, useful for debugging. |
| `error` | ErrorInfo \| None | Present iff `ok=False`. |

`ImageOut` fields: `path` (absolute), `width`, `height`, `seed`, `remote_id`, `remote_url`.

`ErrorInfo` fields: `code` (stable identifier), `message` (human-readable), `retryable` (bool).

## Capabilities

The `capabilities` dict tells callers what the backend supports so they can adapt without making blind calls. Recommended keys:

| Key | Type | Meaning |
|-----|------|---------|
| `max_n` | int | Maximum images per call (1 if backend only does single images). |
| `refs_direct` | bool | Supports img2img style direct reference. |
| `refs_style` | bool | Supports style-extraction references. |
| `refs_palette` | bool | Supports palette-extraction references. |
| `negative_prompt` | bool | Supports negative prompts. |
| `seed` | bool | Supports deterministic seeds. |
| `sizes` | list[str] | List of accepted `WxH` strings, or `["any"]` if arbitrary. |

Composer skills should consult `capabilities` before populating optional fields, to avoid surprising warnings or silent drops.

## Failure Conventions

- **Argument/config errors**: raise `ValueError`. The CLI translates to exit code 1.
- **Network/API errors**: return a `GenerateResponse` with `ok=False` and an `ErrorInfo`. The CLI exits with code 2.
- **Capability mismatches** (e.g. unsupported size): raise `NotImplementedError` so the caller knows to fall back.
- **Unexpected exceptions**: let them propagate; CLI exits with code 3.

## Output File Conventions

- Default naming: `{model}_{timestamp}_{N}.png`. Adapters may use `req.filename` when `req.n == 1`.
- Always `mkdir -p req.output_dir` first.
- Use `target.write_bytes(...)` rather than streaming PIL etc. — keeps adapters dependency-free.
- Resolve to absolute paths (`Path.resolve()`) before populating `ImageOut.path`.

## When To Add A New Adapter vs Reuse `openai_compat`

If your backend speaks the OpenAI Images wire protocol, just add an entry under `backends:` in your config using `type: openai_compat` and set `base_url`/`extra_headers`/`extra_query` accordingly. No code needed.

Add a new adapter when:
- The wire protocol differs (different request schema, different auth flow).
- The backend has unique capabilities (e.g. controlnets, true reference conditioning).
- The backend is a CLI/binary rather than an HTTP endpoint.
