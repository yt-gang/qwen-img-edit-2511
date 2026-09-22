#!/usr/bin/env python3
"""Resolve a complete RunPod Hugging Face cached-model snapshot."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


class ResolutionError(ValueError):
    """The configured cache repository cannot be used safely."""


def _manifest(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ResolutionError("model manifest is unavailable") from exc


def _complete(snapshot: Path, manifest: dict) -> bool:
    try:
        return all(
            (candidate := snapshot / item["target"]).is_file()
            and candidate.stat().st_size == int(item["size"])
            for item in manifest["files"]
        )
    except (OSError, KeyError, TypeError, ValueError):
        return False


def resolve_model_base(*, manifest_path: Path | None = None) -> Path:
    fallback = Path(os.environ.get("QWEN_MODEL_FALLBACK", "/runpod-volume/models"))
    repo_id = os.environ.get("QWEN_CACHED_MODEL_REPO", "").strip().strip("/")
    if not repo_id:
        return fallback
    parts = repo_id.split("/")
    if len(parts) != 2 or any(part in {"", ".", ".."} for part in parts):
        raise ResolutionError("QWEN_CACHED_MODEL_REPO must be org/name")

    manifest = _manifest(
        manifest_path
        or Path(os.environ.get("MODEL_MANIFEST_PATH", "/opt/catline/models.json"))
    )
    cache_root = Path(
        os.environ.get("QWEN_CACHE_ROOT", "/runpod-volume/huggingface-cache/hub")
    )
    repository = cache_root / f"models--{repo_id.replace('/', '--')}"
    candidates: list[Path] = []
    try:
        revision = (repository / "refs" / "main").read_text(encoding="utf-8").strip()
        if revision:
            candidates.append(repository / "snapshots" / revision)
    except OSError:
        pass
    snapshots = repository / "snapshots"
    if snapshots.is_dir():
        candidates.extend(
            path
            for path in sorted(snapshots.iterdir(), reverse=True)
            if path.is_dir() and path not in candidates
        )
    for candidate in candidates:
        if _complete(candidate, manifest):
            return candidate
    if os.environ.get("QWEN_REQUIRE_CACHED_MODEL", "").lower() == "true":
        raise ResolutionError(
            f"cached model snapshot is missing or incomplete for {repo_id}"
        )
    return fallback


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args()
    try:
        print(resolve_model_base(manifest_path=args.manifest))
    except ResolutionError as exc:
        raise SystemExit(str(exc)) from None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
