# Mapping Schema

`{output_root}/{slug}/.mapping.json` tracks the relationship between planned illustrations, their generated files, and any remote URLs. Updated incrementally as `dispatch.py` runs.

## Schema

```json
{
  "article_slug": "my-article",
  "source": {
    "type": "markdown",
    "path": "/abs/path/to/article.md",
    "url": null,
    "doc_id": null
  },
  "output_dir": "/abs/output/my-article",
  "mode": "illustration",
  "default_output_dir_kind": "imgs-subdir",
  "mappings": [
    {
      "illustration_id": "01",
      "filename": "01-infographic-overview.png",
      "local_path": "imgs/my-article/01-infographic-overview.png",
      "absolute_path": "/abs/output/my-article/01-infographic-overview.png",
      "remote_url": "https://cdn.example.com/abc123.png",
      "remote_id": "creative_abc123",
      "backend": "openai_images",
      "model": "gpt-image-1",
      "seed": 12345,
      "prompt_file": "prompts/01-infographic-overview.md",
      "position": "Introduction / the burst problem",
      "alt_text": "Two side-by-side line charts showing the gap between average and peak request rates",
      "status": "ok",
      "updated_at": "2026-06-01T15:30:00Z"
    },
    {
      "illustration_id": "02",
      "filename": "02-framework-token-bucket.png",
      "status": "pending",
      "prompt_file": "prompts/02-framework-token-bucket.md"
    },
    {
      "illustration_id": "03",
      "filename": "03-framework-leaky-vs-token.png",
      "status": "error",
      "error": {
        "code": "HTTP_429",
        "message": "rate limited",
        "attempts": 2
      },
      "prompt_file": "prompts/03-framework-leaky-vs-token.md"
    }
  ]
}
```

## Field Reference

### Top-level

| Field | Required | Notes |
|-------|----------|-------|
| `article_slug` | yes | Matches `outline.md` frontmatter. |
| `source` | yes | Identifies the original document. |
| `output_dir` | yes | Absolute path; the directory holding outline.md / prompts / images. |
| `mode` | yes | `illustration` / `cover` / `both`. |
| `default_output_dir_kind` | yes | One of `imgs-subdir / same-dir / illustrations-subdir / independent`. Drives relative-path calculation for writeback. |
| `mappings` | yes | List of per-illustration entries. |

### `source`

| Field | When |
|-------|------|
| `type` | always — one of `markdown`, `yuque_internal`, `yuque_public`, `text` |
| `path` | for `markdown` and `text` (when from a file) |
| `url` | for `yuque_internal` and `yuque_public` |
| `doc_id` | resolved by yuque ingest adapters via `skylark_resolve_url`; used by writeback |

### Per-mapping

| Field | Required | Notes |
|-------|----------|-------|
| `illustration_id` | yes | `"01"`, `"02"`, ... — matches the outline block index. Use `"cover"` for cover-mode entries. |
| `filename` | yes | Local filename (no path). |
| `local_path` | yes after success | Relative to source document directory; used in markdown image syntax. Computed from `default_output_dir_kind`. |
| `absolute_path` | yes after success | Absolute filesystem path. |
| `remote_url` | when backend provides | URL the image is publicly reachable at. Used by yuque-internal writeback. |
| `remote_id` | when backend provides | Backend-specific identifier. |
| `backend` | yes after success | The backend name that produced this image. |
| `model` | yes after success | Resolved model id. |
| `seed` | when backend supports | Useful for reproducibility / iteration. |
| `prompt_file` | yes | Path (relative to output_dir) to the prompt file that produced this image. |
| `position` | yes | Copied from outline.md `Position` — writeback uses this to find the insertion point. |
| `alt_text` | yes after success | Used as the alt= for the markdown image syntax. |
| `status` | yes | `pending` / `ok` / `error` / `skipped`. |
| `error` | when status=error | `{code, message, attempts}` — code matches `illustration-image-backend/references/error-codes.md`. |
| `updated_at` | yes | ISO 8601 UTC timestamp of last write. |

## Lifecycle

1. `plan.py` writes the initial `.mapping.json` with one entry per planned illustration, all `status=pending`, only `illustration_id`, `filename`, `prompt_file`, `position` populated.
2. `compose.py` reads the outline, writes prompt files, does not touch mapping.
3. `dispatch.py` iterates pending entries. After each generation:
   - On success: update with `local_path`, `absolute_path`, `remote_url`, `backend`, `model`, `seed`, `alt_text`, `status: ok`, `updated_at`.
   - On error: update with `status: error`, `error: {code, message, attempts}`, `updated_at`.
4. `writeback.py` reads ok entries and patches the source document.

Re-running `dispatch.py` should skip `ok` entries by default. Use `--regenerate <id1,id2>` or `--regenerate-all` to force regeneration.

## Atomic Writes

To avoid corruption on Ctrl-C, write to `.mapping.json.tmp` and `os.replace()` to the final name.
