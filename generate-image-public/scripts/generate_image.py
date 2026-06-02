#!/usr/bin/env python3
"""Generate images via OpenAI Images API (gpt-image-1).

Stdout: absolute path to the saved PNG.
Stderr: progress and errors.

Exit codes:
  0 success
  1 argument / config error
  2 API error
  3 other error
"""

import argparse
import base64
import datetime as _dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request


DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-image-1"
DEFAULT_SIZE = "1536x1024"
DEFAULT_QUALITY = "high"


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _resolve_token(cli_token: str | None) -> str:
    token = cli_token or os.environ.get("OPENAI_API_KEY")
    if not token:
        _log("error: missing OpenAI API key. Pass --token or set OPENAI_API_KEY.")
        sys.exit(1)
    return token


def _resolve_base_url(cli_url: str | None) -> str:
    return (cli_url or os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def _call_api(base_url: str, token: str, model: str, prompt: str, size: str, quality: str, n: int) -> dict:
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "n": n,
        "size": size,
        "quality": quality,
    }).encode("utf-8")

    req = urllib.request.Request(
        url=f"{base_url}/images/generations",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        _log(f"error: HTTP {e.code} from {base_url}/images/generations")
        _log(detail)
        sys.exit(2)
    except urllib.error.URLError as e:
        _log(f"error: network failure calling {base_url}: {e}")
        sys.exit(2)


def _save_images(payload: dict, output_dir: pathlib.Path, model: str) -> list[pathlib.Path]:
    data = payload.get("data") or []
    if not data:
        _log(f"error: API returned no images. Raw: {json.dumps(payload)[:500]}")
        sys.exit(2)

    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d%H%M%S")
    saved: list[pathlib.Path] = []

    for idx, item in enumerate(data, start=1):
        b64 = item.get("b64_json")
        url = item.get("url")
        filename = f"{model.replace('/', '_')}_{stamp}_{idx}.png"
        target = output_dir / filename

        if b64:
            target.write_bytes(base64.b64decode(b64))
        elif url:
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    target.write_bytes(r.read())
            except urllib.error.URLError as e:
                _log(f"error: failed to download image {idx} from {url}: {e}")
                sys.exit(2)
        else:
            _log(f"error: image {idx} has neither b64_json nor url")
            sys.exit(2)

        saved.append(target.resolve())
        _log(f"saved: {target.resolve()}")

    return saved


def main() -> None:
    p = argparse.ArgumentParser(
        description="Generate images via OpenAI Images API (public, no company gateway).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--prompt", "-p", required=True, help="Image description.")
    p.add_argument("--token", default=None, help="OpenAI API key (overrides OPENAI_API_KEY).")
    p.add_argument("--base-url", default=None, help="API base URL (overrides OPENAI_BASE_URL).")
    p.add_argument("--model", "-m", default=os.environ.get("OPENAI_IMAGE_MODEL", DEFAULT_MODEL),
                   help="Model name. gpt-image-1 supports up to 1536x1024 / 1024x1536 / 1024x1024.")
    p.add_argument("--size", default=DEFAULT_SIZE,
                   help="Image size. For 16:9 editorial: 1536x1024.")
    p.add_argument("--quality", default=DEFAULT_QUALITY,
                   help="low | medium | high | auto.")
    p.add_argument("-n", "--count", type=int, default=1, help="How many images to generate.")
    p.add_argument("--output-dir", "-o", default=os.environ.get("IMAGE_OUTPUT_DIR", ".image_process"),
                   help="Where to save PNGs.")

    args = p.parse_args()

    token = _resolve_token(args.token)
    base_url = _resolve_base_url(args.base_url)
    output_dir = pathlib.Path(args.output_dir).expanduser()

    _log(f"model={args.model} size={args.size} quality={args.quality} n={args.count} base={base_url}")

    try:
        payload = _call_api(base_url, token, args.model, args.prompt, args.size, args.quality, args.count)
        saved = _save_images(payload, output_dir, args.model)
    except SystemExit:
        raise
    except Exception as e:
        _log(f"error: unexpected failure: {e}")
        sys.exit(3)

    for path in saved:
        print(str(path))


if __name__ == "__main__":
    main()
