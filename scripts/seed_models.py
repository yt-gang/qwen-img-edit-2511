#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("/opt/catline/models.json"))
    parser.add_argument("--base", type=Path, default=Path("/runpod-volume/models"))
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    for item in manifest["files"]:
        target = args.base / item["target"]
        if target.is_file() and target.stat().st_size == item["size"]:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            "hf", "download", item["repo"], item["source"], "--revision", item["revision"],
            "--local-dir", str(target.parent / ".download"),
        ], check=True)
        downloaded = target.parent / ".download" / item["source"]
        downloaded.replace(target)
    subprocess.run([
        "python", "/opt/catline/verify_models.py", "--manifest", str(args.manifest),
        "--base", str(args.base), "--full",
    ], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
