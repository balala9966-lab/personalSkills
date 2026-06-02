"""Ingest dispatcher: pick the right adapter for a source string.

Public-network version: yuque_internal adapter is not bundled.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE / "ingest") not in sys.path:
    sys.path.insert(0, str(_HERE / "ingest"))

import markdown as md_adapter
import yuque_public as yp_adapter
import text as text_adapter


_ADAPTERS = [yp_adapter, md_adapter, text_adapter]


def detect_and_load(source: str, **kwargs: Any) -> dict[str, Any]:
    """Try each adapter's detect(); return load() result from the first match.

    Pass adapter-specific kwargs through (e.g. prefetched_body).
    """
    for adapter in _ADAPTERS:
        if adapter.detect(source):
            import inspect
            sig = inspect.signature(adapter.load)
            accepted = {k: v for k, v in kwargs.items() if k in sig.parameters}
            return adapter.load(source, **accepted)
    raise ValueError(
        f"no ingest adapter matched source {source!r}. "
        f"supported: local .md, .txt, stdin '-', http(s) yuque.com URLs."
    )


def adapter_for_source_type(source_type: str):
    """Find the adapter module that handles a given source type id."""
    mapping = {
        "markdown": md_adapter,
        "text": text_adapter,
        "yuque_public": yp_adapter,
    }
    if source_type not in mapping:
        raise ValueError(
            f"unknown source type {source_type!r}. "
            f"public version supports: markdown, text, yuque_public."
        )
    return mapping[source_type]
