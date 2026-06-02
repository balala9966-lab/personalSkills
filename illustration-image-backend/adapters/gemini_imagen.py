"""Gemini Imagen adapter (public network).

Uses Google's `google-generativeai` SDK. If the package is not installed,
the adapter is registered but `available()` returns False with an actionable
message — the CLI surfaces this without crashing the whole process.

Capabilities (Imagen 3 / 4):
- txt2img: yes
- img2img / refs: not via the public API at time of writing
- multiple images per call: yes (number_of_images up to 4)
- seed: yes (via `seed` request param)
"""

from __future__ import annotations

import datetime as _dt
import os
import time
from pathlib import Path
from typing import Any

from base import (
    ErrorInfo, GenerateRequest, GenerateResponse, ImageBackend, ImageOut,
)
from registry import register


try:
    import google.generativeai as _genai  # type: ignore
    _GENAI_AVAILABLE = True
except ImportError:
    _genai = None
    _GENAI_AVAILABLE = False


class GeminiImagenBackend(ImageBackend):
    name = "gemini_imagen"
    capabilities = {
        "max_n": 4,
        "refs_direct": False,
        "refs_style": False,
        "refs_palette": False,
        "negative_prompt": True,
        "seed": True,
        "sizes": ["1024x1024", "1024x768", "768x1024", "1408x768", "768x1408"],
    }

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.default_model = config.get("default_model", "imagen-3.0-generate-002")

    def available(self) -> tuple[bool, str]:
        if not _GENAI_AVAILABLE:
            return False, ("google-generativeai not installed. "
                           "run: pip install google-generativeai")
        env = self.config.get("api_key_env", "GEMINI_API_KEY")
        if not os.environ.get(env):
            return False, f"missing env var {env}"
        return True, ""

    def generate(self, req: GenerateRequest) -> GenerateResponse:
        t0 = time.perf_counter()
        ok, reason = self.available()
        if not ok:
            return GenerateResponse(
                ok=False, backend=self.name, model=req.model or self.default_model,
                elapsed_ms=self._stamp_response(t0),
                error=ErrorInfo(code="UNAVAILABLE", message=reason),
            )

        env = self.config.get("api_key_env", "GEMINI_API_KEY")
        _genai.configure(api_key=os.environ[env])
        model = req.model or self.default_model

        try:
            generation_model = _genai.ImageGenerationModel.from_pretrained(model)
            result = generation_model.generate_images(
                prompt=req.prompt,
                number_of_images=req.n,
                negative_prompt=req.negative_prompt,
                aspect_ratio=self._infer_aspect(req.width, req.height),
                seed=req.seed,
            )
        except Exception as e:
            return GenerateResponse(
                ok=False, backend=self.name, model=model,
                elapsed_ms=self._stamp_response(t0),
                error=ErrorInfo(code="API_ERROR", message=str(e),
                                retryable="rate" in str(e).lower()),
            )

        saved = self._save_results(result, req, model)
        if not saved:
            return GenerateResponse(
                ok=False, backend=self.name, model=model,
                elapsed_ms=self._stamp_response(t0),
                error=ErrorInfo(code="EMPTY_RESPONSE", message="no images returned"),
            )

        return GenerateResponse(
            ok=True, backend=self.name, model=model,
            elapsed_ms=self._stamp_response(t0), images=saved,
        )

    def _infer_aspect(self, w: int, h: int) -> str:
        ratio = w / h if h else 1.0
        if abs(ratio - 1.0) < 0.05:
            return "1:1"
        if ratio > 1.5:
            return "16:9"
        if ratio > 1.2:
            return "4:3"
        if ratio < 0.66:
            return "9:16"
        if ratio < 0.85:
            return "3:4"
        return "1:1"

    def _save_results(self, result: Any, req: GenerateRequest, model: str) -> list[ImageOut]:
        output_dir = Path(req.output_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = _dt.datetime.now().strftime("%Y%m%d%H%M%S")
        out: list[ImageOut] = []
        images = getattr(result, "images", None) or list(result)
        for idx, img in enumerate(images, start=1):
            fname = req.filename if req.filename and req.n == 1 else \
                f"{model.replace('/', '_')}_{stamp}_{idx}.png"
            target = output_dir / fname
            raw = getattr(img, "_image_bytes", None) or getattr(img, "image_bytes", None)
            if raw is None and hasattr(img, "save"):
                img.save(target)
            elif raw is not None:
                target.write_bytes(raw)
            else:
                continue
            out.append(ImageOut(
                path=str(target.resolve()),
                width=req.width, height=req.height,
            ))
        return out


register("gemini_imagen", GeminiImagenBackend)
