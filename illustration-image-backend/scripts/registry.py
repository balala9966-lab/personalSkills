"""Backend registry. Adapters call register() at module-load time."""

from __future__ import annotations

from typing import Any

from base import ImageBackend


_REGISTRY: dict[str, type[ImageBackend]] = {}


def register(type_name: str, cls: type[ImageBackend]) -> None:
    if type_name in _REGISTRY:
        if _REGISTRY[type_name] is cls:
            return  # idempotent re-import is fine
        raise ValueError(f"backend type {type_name!r} already registered to a different class")
    _REGISTRY[type_name] = cls


def get_backend(type_name: str, config: dict[str, Any]) -> ImageBackend:
    if type_name not in _REGISTRY:
        raise ValueError(
            f"unknown backend type {type_name!r}. "
            f"available: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[type_name](config)


def list_backends() -> list[str]:
    return sorted(_REGISTRY)
