from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _default_workflow() -> dict:
    module = ast.parse((ROOT / "handler.py").read_text(encoding="utf-8"))
    assignment = next(
        node
        for node in module.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "DEFAULT_WORKFLOW" for target in node.targets)
    )
    return ast.literal_eval(assignment.value)


def test_comfyui_version_is_pinned_consistently():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    bake = (ROOT / "docker-bake.hcl").read_text(encoding="utf-8")

    docker_version = re.search(r"^ARG COMFYUI_VERSION=(\S+)$", dockerfile, re.MULTILINE).group(1)
    bake_version = re.search(
        r'variable "COMFYUI_VERSION"\s*\{\s*default = "([^"]+)"', bake, re.MULTILINE
    ).group(1)

    assert docker_version == "v0.36.0"
    assert bake_version == docker_version


def test_cfg_norm_matches_official_qwen_2511_workflow():
    workflow = _default_workflow()

    assert workflow["170:152"]["class_type"] == "CFGNorm"
    assert workflow["170:152"]["inputs"]["strength"] == 1
    assert workflow["170:152"]["inputs"]["pre_cfg"] is False
    assert workflow["170:161"]["inputs"]["unet_name"] == "qwen_image_edit_2511_fp8mixed.safetensors"
    assert workflow["170:162"]["inputs"]["clip_name"] == "qwen_2.5_vl_7b_fp8_scaled.safetensors"
    assert workflow["170:146"]["inputs"]["vae_name"] == "qwen_image_vae.safetensors"
