"""OpenAI Images API adapter (public network).

Supports gpt-image-1 and dall-e-3. Uses only Python stdlib (urllib).

Capabilities:
- txt2img: yes
- img2img / refs: NO via /images/generations; would need /images/edits which
  is mask-based not reference-conditioning. For now we skip refs and surface
  a warning.
- multiple images per call: yes (gpt-image-1 supports n>=1)
- seed: not exposed by the API as of this writing
"""

from __future__ import annotations

import base64
import datetime as _dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from base import (
    ErrorInfo, GenerateRequest, GenerateResponse, ImageBackend, ImageOut,
)
from registry import register


class OpenAIImagesBackend(ImageBackend):
    name = "openai_images"
    capabilities = {
        "max_n": 4,
        "refs_direct": False,
        "refs_style": False,
        "refs_palette": False,
        "negative_prompt": False,
        "seed": False,
        "sizes": ["1024x1024", "1536x1024", "1024x1536", "auto"],
    }

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.base_url = (config.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = self._resolve_api_key()
        self.default_model = config.get("default_model", "gpt-image-1")
        self.timeout = int(config.get("timeout", 180))
        self.quality = config.get("quality", "high")

    def _resolve_api_key(self) -> str | None:
        env_name = self.config.get("api_key_env", "OPENAI_API_KEY")
        return os.environ.get(env_name)

    def available(self) -> tuple[bool, str]:
        if not self.api_key:
            env = self.config.get("api_key_env", "OPENAI_API_KEY")
            return False, f"missing env var {env}"
        return True, ""

    def generate(self, req: GenerateRequest) -> GenerateResponse:
        t0 = time.perf_counter()
        ok, reason = self.available()
        if not ok:
            return GenerateResponse(
                ok=False, backend=self.name, model=req.model or self.default_model,
                elapsed_ms=self._stamp_response(t0),
                error=ErrorInfo(code="MISSING_CREDENTIAL", message=reason),
            )

        if req.refs:
            print(f"[{self.name}] warning: refs not supported by /images/generations; ignoring",
                  file=sys.stderr)

        size = f"{req.width}x{req.height}"
        model = req.model or self.default_model
        body = json.dumps({
            "model": model,
            "prompt": req.prompt,
            "n": req.n,
            "size": size,
            "quality": req.extra.get("quality", self.quality),
        }).encode("utf-8")

        url = f"{self.base_url}/images/generations"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        for k, v in (self.config.get("extra_headers") or {}).items():
            headers[k] = v
        if extra_query := self.config.get("extra_query"):
            qs = "&".join(f"{k}={v}" for k, v in extra_query.items())
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{qs}"

        try:
            request = urllib.request.Request(url, data=body, method="POST", headers=headers)
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return GenerateResponse(
                ok=False, backend=self.name, model=model,
                elapsed_ms=self._stamp_response(t0),
                error=ErrorInfo(code=f"HTTP_{e.code}",
                                message=e.read().decode("utf-8", errors="replace"),
                                retryable=e.code in (429, 500, 502, 503, 504)),
            )
        except urllib.error.URLError as e:
            return GenerateResponse(
                ok=False, backend=self.name, model=model,
                elapsed_ms=self._stamp_response(t0),
                error=ErrorInfo(code="NETWORK", message=str(e), retryable=True),
            )

        saved = self._save_payload(payload, req, model)
        if not saved:
            return GenerateResponse(
                ok=False, backend=self.name, model=model,
                elapsed_ms=self._stamp_response(t0), raw=payload,
                error=ErrorInfo(code="EMPTY_RESPONSE", message="API returned no images"),
            )

        return GenerateResponse(
            ok=True, backend=self.name, model=model,
            elapsed_ms=self._stamp_response(t0),
            images=saved, raw=payload,
        )

    def _save_payload(self, payload: dict[str, Any], req: GenerateRequest, model: str) -> list[ImageOut]:
        data = payload.get("data") or []
        if not data:
            return []
        output_dir = Path(req.output_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = _dt.datetime.now().strftime("%Y%m%d%H%M%S")
        out: list[ImageOut] = []
        for idx, item in enumerate(data, start=1):
            b64 = item.get("b64_json")
            url = item.get("url")
            fname = req.filename if req.filename and req.n == 1 else \
                f"{model.replace('/', '_')}_{stamp}_{idx}.png"
            target = output_dir / fname
            if b64:
                target.write_bytes(base64.b64decode(b64))
            elif url:
                with urllib.request.urlopen(url, timeout=60) as r:
                    target.write_bytes(r.read())
            else:
                continue
            out.append(ImageOut(
                path=str(target.resolve()),
                width=req.width, height=req.height,
                remote_url=url,
            ))
        return out


register("openai_images", OpenAIImagesBackend)
