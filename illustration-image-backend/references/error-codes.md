# Error Codes

Stable identifiers reported in `GenerateResponse.error.code`. Use these in catch / retry logic; the `message` field can change without notice.

## CLI-level

| Code | When | Action |
|------|------|--------|
| (exit 1) | Bad arguments, unknown backend, missing required field | Fix invocation. |
| (exit 3) | Unexpected Python exception | File a bug. Include the stderr traceback. |

## Adapter-level

| Code | Backends | When | Retryable | Action |
|------|----------|------|-----------|--------|
| `MISSING_CREDENTIAL` | openai_images, openai_compat | Required env var unset | no | Set the env var, retry. |
| `UNAVAILABLE` | gemini_imagen | Optional pip pkg missing | no | Install the dependency. |
| `HTTP_401` | openai_images, openai_compat | Auth rejected by server | no | Rotate / verify API key. |
| `HTTP_403` | openai_images, openai_compat | Forbidden | no | Check account/model permissions. |
| `HTTP_400` | openai_images, openai_compat | Bad request body (size, model, content policy) | no | Inspect `message`. Common cause: requesting an unsupported size for the model. |
| `HTTP_429` | openai_images, openai_compat | Rate limited | yes | Back off and retry. |
| `HTTP_500..504` | openai_images, openai_compat | Server-side errors | yes | Retry with exponential backoff. |
| `NETWORK` | openai_images, openai_compat | DNS, TCP, TLS failures | yes | Check connectivity / proxy. |
| `API_ERROR` | gemini_imagen | SDK raised non-rate-limit error | partial | Check `message`. |
| `EMPTY_RESPONSE` | all | API succeeded but returned no usable image data | no | Inspect `raw`. Often a content-policy soft refusal. |

## Retryable Logic Tip

If your composer wants to auto-retry, check `error.retryable`. The CLI itself does not auto-retry — staying explicit means the composer's policy (max attempts, backoff) is visible in one place.
