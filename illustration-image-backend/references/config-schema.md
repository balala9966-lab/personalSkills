# Config Schema

The `backends.yaml` config controls which backends are visible to the CLI and how each one authenticates and routes.

## Top-Level Keys

| Key | Type | Required | Default | Notes |
|-----|------|----------|---------|-------|
| `default_backend` | string | no | `openai_images` | Used when neither `--backend` nor `--alias` is passed. |
| `fallback_chain` | list[string] | no | `[]` | (Reserved for future use; currently informational.) |
| `backends` | mapping | yes | — | One entry per configured backend. Key is the human-friendly name used with `--backend`. |
| `aliases` | mapping | no | `{}` | Friendly shortcuts that resolve to `{backend, model}`. |

## Backend Entry Schema

```yaml
backends:
  <NAME>:
    type: <TYPE_ID>           # Required. Must match a registered adapter type.
    api_key_env: <ENV_NAME>   # For HTTP backends. Adapter reads os.environ[ENV_NAME].
    base_url: <URL>           # For HTTP backends. Default depends on adapter.
    default_model: <MODEL>    # Used when req.model is None.
    timeout: <SECONDS>        # Default depends on adapter.
    extra_headers: { ... }    # HTTP backends: merged into request headers.
    extra_query: { ... }      # HTTP backends: merged into URL query string.
    # Any other key is passed through to the adapter via self.config.
```

### Backend type → recognized keys

| Type | Keys |
|------|------|
| `openai_images` | `api_key_env`, `base_url`, `default_model`, `timeout`, `quality`, `extra_headers`, `extra_query` |
| `openai_compat` | same as `openai_images` |
| `gemini_imagen` | `api_key_env`, `default_model`, `timeout` |

## Alias Entry Schema

```yaml
aliases:
  <ALIAS_NAME>:
    backend: <NAME-FROM-BACKENDS-MAP>
    model: <MODEL_ID>
```

When `--alias <ALIAS_NAME>` is passed:
1. `backend` is resolved to a backend entry.
2. `model` is used as `req.model` unless overridden by `--model`.

## Config Search Order

The CLI looks for `backends.yaml` in this order:

1. `--config` CLI argument
2. `$ILLUSTRATION_IMAGE_BACKEND_CONFIG` environment variable
3. `./illustration-image-backend.yaml` (project-local)
4. `$XDG_CONFIG_HOME/illustration-image-backend/backends.yaml` (or `~/.config/illustration-illustration-image-backend/backends.yaml`)
5. `~/.illustration-illustration-image-backend/backends.yaml`

If none found, the CLI uses zero-config defaults — handy for one-off testing but you'll want a real config for daily use.

## Validation

There is no explicit schema validation. Mistakes surface as:
- Unknown `type` → CLI exits 1 with `unknown backend type 'X'. available: [...]`.
- Missing API key → backend's `available()` returns False; CLI exits 2 with `MISSING_CREDENTIAL`.
- Missing CLI binary → backend's `available()` returns False; CLI exits 2 with `UNAVAILABLE`.

## Minimal Config Example

```yaml
default_backend: openai_images
backends:
  openai_images:
    type: openai_images
    api_key_env: OPENAI_API_KEY
```

That's it. Everything else has sensible defaults.

## Multiple Endpoints Of The Same Kind

You can configure several `openai_compat` backends pointing at different proxies:

```yaml
backends:
  azure_west:
    type: openai_compat
    api_key_env: AZURE_OPENAI_KEY_WEST
    base_url: https://west.openai.azure.com/openai/deployments/gpt-image-1
    extra_query: { api-version: "2024-08-01-preview" }
  azure_east:
    type: openai_compat
    api_key_env: AZURE_OPENAI_KEY_EAST
    base_url: https://east.openai.azure.com/openai/deployments/gpt-image-1
    extra_query: { api-version: "2024-08-01-preview" }
```

Both are addressable via `--backend azure_west` / `--backend azure_east`.
