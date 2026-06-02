"""Image backend ABC and shared data classes.

Backends implement a single `generate` method that takes a normalized
GenerateRequest and returns a normalized GenerateResponse.

Failure conventions:
- Argument/config errors: raise ValueError; CLI translates to exit code 1.
- API/network errors: return a GenerateResponse with ok=False and a
  populated ErrorInfo; the CLI translates to exit code 2.
- Capability mismatches (e.g. unsupported size): raise NotImplementedError.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


RefRole = Literal["direct", "style", "palette"]


@dataclass
class Reference:
    """A user-supplied reference image.

    role=direct  -> the generator should follow this image closely (img2img)
    role=style   -> extract visual style hints only
    role=palette -> extract color palette only
    """
    path: str
    role: RefRole = "direct"
    weight: float = 1.0


@dataclass
class GenerateRequest:
    prompt: str
    negative_prompt: str | None = None
    width: int = 1024
    height: int = 1024
    n: int = 1
    seed: int | None = None
    refs: list[Reference] = field(default_factory=list)
    output_dir: str = ".image_process"
    filename: str | None = None
    model: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImageOut:
    path: str
    width: int
    height: int
    seed: int | None = None
    remote_id: str | None = None
    remote_url: str | None = None


@dataclass
class ErrorInfo:
    code: str
    message: str
    retryable: bool = False


@dataclass
class GenerateResponse:
    ok: bool
    backend: str
    model: str
    elapsed_ms: int
    images: list[ImageOut] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    error: ErrorInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def request_from_dict(d: dict[str, Any]) -> GenerateRequest:
    refs = [Reference(**r) for r in d.get("refs", [])]
    payload = {**d, "refs": refs}
    return GenerateRequest(**payload)


class ImageBackend(ABC):
    """Abstract base for an image-generation backend.

    Concrete backends:
    - Set `name` to a stable lowercase identifier.
    - Set `capabilities` to declare what they support so callers can
      adapt without making blind calls.
    - Implement `generate(req)` returning a GenerateResponse.
    - Override `available()` when the backend depends on external CLI or
      optional Python packages.
    """

    name: str = "unnamed"
    capabilities: dict[str, Any] = {
        "max_n": 1,
        "refs_direct": False,
        "refs_style": False,
        "refs_palette": False,
        "negative_prompt": False,
        "seed": False,
        "sizes": [],
    }

    def __init__(self, config: dict[str, Any]):
        self.config = config

    @abstractmethod
    def generate(self, req: GenerateRequest) -> GenerateResponse: ...

    def available(self) -> tuple[bool, str]:
        return True, ""

    def _stamp_response(self, t0: float) -> int:
        return int((time.perf_counter() - t0) * 1000)
