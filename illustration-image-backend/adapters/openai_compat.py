"""OpenAI-compatible backend.

For Azure OpenAI, OpenRouter, LiteLLM, and any other endpoint that mimics
the OpenAI Images API. The only differences from `openai_images` are:
- `base_url` typically points at a non-openai.com host
- some providers (Azure) require extra query params like api-version
- some providers add custom headers (x-title, x-organization, etc.)

All of those are handled via config:
  base_url, api_key_env, extra_headers, extra_query

Inherits from OpenAIImagesBackend with no behavioral changes — it exists
as a separate registered backend so config files can talk about "this is
OpenAI direct" vs "this is an OpenAI-compatible proxy" semantically.
"""

from __future__ import annotations

from openai_images import OpenAIImagesBackend
from registry import register


class OpenAICompatBackend(OpenAIImagesBackend):
    name = "openai_compat"


register("openai_compat", OpenAICompatBackend)
