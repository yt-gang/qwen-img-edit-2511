from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "resolve_model_base.py"
SPEC = importlib.util.spec_from_file_location("resolve_model_base", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _manifest(tmp_path: Path) -> Path:
    path = tmp_path / "models.json"
    path.write_text(
        json.dumps(
            {"files": [{"target": "diffusion_models/model.safetensors", "size": 5}]}
        )
    )
    return path


def test_prefers_complete_cached_snapshot(monkeypatch, tmp_path):
    repo = tmp_path / "hub" / "models--yt-gang-prod--qwen-edit-2511-cache"
    snapshot = repo / "snapshots" / "abc123"
    model = snapshot / "diffusion_models" / "model.safetensors"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"model")
    (repo / "refs").mkdir()
    (repo / "refs" / "main").write_text("abc123\n")
    monkeypatch.setenv("QWEN_CACHED_MODEL_REPO", "yt-gang-prod/qwen-edit-2511-cache")
    monkeypatch.setenv("QWEN_CACHE_ROOT", str(tmp_path / "hub"))
    assert MODULE.resolve_model_base(manifest_path=_manifest(tmp_path)) == snapshot


def test_incomplete_cache_falls_back(monkeypatch, tmp_path):
    fallback = tmp_path / "models"
    monkeypatch.setenv("QWEN_MODEL_FALLBACK", str(fallback))
    monkeypatch.setenv("QWEN_CACHED_MODEL_REPO", "yt-gang-prod/missing")
    monkeypatch.setenv("QWEN_CACHE_ROOT", str(tmp_path / "hub"))
    assert MODULE.resolve_model_base(manifest_path=_manifest(tmp_path)) == fallback


def test_required_cache_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("QWEN_CACHED_MODEL_REPO", "yt-gang-prod/missing")
    monkeypatch.setenv("QWEN_CACHE_ROOT", str(tmp_path / "hub"))
    monkeypatch.setenv("QWEN_REQUIRE_CACHED_MODEL", "true")
    with pytest.raises(MODULE.ResolutionError, match="missing or incomplete"):
        MODULE.resolve_model_base(manifest_path=_manifest(tmp_path))


def test_rejects_invalid_repository_name(monkeypatch, tmp_path):
    monkeypatch.setenv("QWEN_CACHED_MODEL_REPO", "invalid")
    with pytest.raises(MODULE.ResolutionError, match="org/name"):
        MODULE.resolve_model_base(manifest_path=_manifest(tmp_path))
