#!/usr/bin/env python3
"""Step 1+2 of the workflow: ingest a source, analyze content, write outline.md skeleton.

Outputs:
  - {output_root}/{slug}/outline.md (no per-illustration blocks yet — those are
    added by plan.py once the user has confirmed type/style/density)
  - prints a JSON summary of the analysis to stdout
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _setup_imports() -> None:
    here = Path(__file__).resolve().parent
    repo = here.parent
    for p in (here, repo / "adapters", repo / "adapters" / "ingest"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


_setup_imports()

import preferences           # noqa: E402
import styles_loader         # noqa: E402
import util                  # noqa: E402
import ingest_dispatcher     # noqa: E402


CONTENT_TYPE_SIGNALS = {
    "technical": [r"\bAPI\b", r"\bSDK\b", r"endpoint", r"接口", r"参数", r"协议"],
    "tutorial":  [r"\bstep\b", r"install", r"how to", r"第一步", r"教程", r"配置"],
    "methodology": [r"architecture", r"system", r"module", r"component", r"架构", r"体系"],
    "data":      [r"\d+%", r"MAU", r"metric", r"环比", r"同比", r"指标"],
    "comparison": [r"\bvs\b", r"versus", r"compared to", r"vs\.", r"对比"],
    "narrative": [r"^I ", r" my ", r"when I", r"我觉得", r"个人"],
    "opinion":   [r"should", r"shouldn't", r"\bwrong\b", r"反思", r"看法"],
    "history":   [r"\b\d{4}\b", r"decade", r"since", r"历经", r"演进"],
    "academic":  [r"hypothesis", r"experiment", r"result", r"论文"],
    "saas":      [r"\buser\b", r"pricing", r"onboarding", r"\bproduct\b"],
}


def detect_content_type(text: str) -> str:
    scores: dict[str, int] = {}
    for ctype, patterns in CONTENT_TYPE_SIGNALS.items():
        scores[ctype] = sum(len(re.findall(p, text, re.IGNORECASE | re.MULTILINE)) for p in patterns)
    if not any(scores.values()):
        return "unknown"
    return max(scores, key=lambda k: scores[k])


def identify_anchor_positions(sections: list[dict], density: str) -> list[dict]:
    """Pick paragraph anchors based on density.

    Strategy:
      - per-section / rich: one anchor per non-empty section
      - balanced: one anchor per H1/H2; not per H3+
      - minimal: just the first one or two anchors
    """
    candidates: list[dict] = []
    for sec in sections:
        if not sec["paragraphs"]:
            continue
        if density == "balanced" and sec["level"] > 2:
            continue
        candidates.append({
            "heading": sec["heading"],
            "level": sec["level"],
            "snippet": sec["paragraphs"][0][:120],
            "position": f"{sec['heading']} / {_short(sec['paragraphs'][0])}" if sec["heading"]
                        else _short(sec["paragraphs"][0]),
        })

    if density == "minimal":
        return candidates[:2]
    if density == "balanced":
        return candidates[:5]
    if density == "rich":
        return candidates[:9]
    return candidates  # per-section


def _short(text: str, max_chars: int = 60) -> str:
    text = text.strip().replace("\n", " ")
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def main() -> int:
    p = argparse.ArgumentParser(description="Step 1+2: ingest + analyze.")
    p.add_argument("source", help="Source path or URL.")
    p.add_argument("--prefetched-body", help="For yuque sources: path to a file containing the body markdown.")
    p.add_argument("--doc-id", help="For yuque_internal: doc_id from skylark_resolve_url.")
    p.add_argument("--output-dir-kind", help="Override default_output_dir from preferences.")
    p.add_argument("--out", help="Write JSON summary here. Default: stdout.")
    args = p.parse_args()

    prefs, prefs_src = preferences.load()
    print(f"[analyze] preferences: {prefs_src or '<defaults>'}", file=sys.stderr)

    kwargs = {}
    if args.prefetched_body:
        body_path = Path(args.prefetched_body).expanduser()
        kwargs["prefetched_body"] = body_path.read_text(encoding="utf-8")
    if args.doc_id:
        kwargs["doc_id"] = args.doc_id

    doc = ingest_dispatcher.detect_and_load(args.source, **kwargs)
    print(f"[analyze] ingest: type={doc['source']['type']} title={doc['title']!r} "
          f"sections={len(doc['sections'])} words={doc['word_count']} lang={doc['language']}",
          file=sys.stderr)

    content_type = detect_content_type(doc["raw"])
    density = styles_loader.density_for_word_count(doc["word_count"])
    first_preset, alt_preset = styles_loader.auto_recommend_preset(content_type)
    anchors = identify_anchor_positions(doc["sections"], density)

    output_dir_kind = args.output_dir_kind or prefs["default_output_dir"]
    output_root = util.compute_output_root(doc["source"], output_dir_kind)
    article_slug = util.article_slug_from_source(doc["source"])
    workdir = util.article_workdir(output_root, article_slug)
    workdir.mkdir(parents=True, exist_ok=True)

    summary = {
        "title": doc["title"],
        "article_slug": article_slug,
        "source": doc["source"],
        "language": doc["language"],
        "word_count": doc["word_count"],
        "section_count": len(doc["sections"]),
        "content_type": content_type,
        "recommended_density": density,
        "recommended_preset": first_preset,
        "alternate_preset": alt_preset,
        "anchors": anchors,
        "output_dir": str(workdir),
        "output_dir_kind": output_dir_kind,
    }

    skeleton = _outline_skeleton(summary, first_preset)
    (workdir / "outline.md").write_text(skeleton, encoding="utf-8")
    print(f"[analyze] wrote {workdir / 'outline.md'}", file=sys.stderr)

    json_out = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(json_out, encoding="utf-8")
    else:
        print(json_out)
    return 0


def _outline_skeleton(summary: dict, preset_id: str) -> str:
    preset = styles_loader.resolve_preset(preset_id)
    src = summary["source"]
    return f"""---
article_slug: {summary['article_slug']}
title: {summary['title']}
type: {preset['type']}
style: {preset['style']}
palette: {preset.get('palette', '')}
density: {summary['recommended_density']}
image_count: 0
mode: illustration
language: {summary['language']}
content_type: {summary['content_type']}
recommended_preset: {summary['recommended_preset']}
alternate_preset: {summary['alternate_preset']}
source_type: {src.get('type', '')}
source_path: {src.get('path') or ''}
source_url: {src.get('url') or ''}
doc_id: {src.get('doc_id') or ''}
output_dir_kind: {summary['output_dir_kind']}
---

<!--
This is a skeleton produced by analyze.py.
Run plan.py with --preset <id> (or --type / --style overrides) to fill in
per-illustration blocks. The recommended preset is `{preset_id}` based on
content_type={summary['content_type']!r}.

Candidate anchor positions (from analyze):
{chr(10).join(f"- {a['position']}" for a in summary['anchors'])}
-->
"""


if __name__ == "__main__":
    sys.exit(main())
