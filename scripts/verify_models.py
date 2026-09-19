#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as model:
        for chunk in iter(lambda: model.read(8 * 1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def manifest_marker(manifest: dict, base: Path) -> Path:
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return base / f".catline-{manifest['name']}-{hashlib.sha256(encoded).hexdigest()[:16]}.verified"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    marker = manifest_marker(manifest, args.base)
    errors = []
    for item in manifest["files"]:
        path = args.base / item["target"]
        if not path.is_file():
            errors.append(f"missing: {item['target']}")
            continue
        if path.stat().st_size != item["size"]:
            errors.append(f"size mismatch: {item['target']}")
            continue
        if args.full and digest(path) != item["sha256"]:
            errors.append(f"sha256 mismatch: {item['target']}")
    if errors:
        marker.unlink(missing_ok=True)
        raise SystemExit("model verification failed: " + "; ".join(errors))
    if args.full:
        marker.write_text("verified\n", encoding="utf-8")
    elif not marker.is_file():
        raise SystemExit(f"full verification marker is missing: {marker}")
    print(marker)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
