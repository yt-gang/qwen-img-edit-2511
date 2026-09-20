"""Catline-specific input/output contract for the Qwen edit worker."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import requests
from PIL import Image, ImageOps

OUTPUT_CONTENT_TYPE = "image/webp"
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
MAX_REFERENCE_BYTES = 25 * 1024 * 1024


class ContractError(ValueError):
    """Safe validation error which never contains signed URL query data."""


@dataclass(frozen=True)
class OutputTarget:
    upload_url: str
    object_key: str
    required_headers: dict[str, str]


def validate_output_target(raw: object) -> OutputTarget:
    if not isinstance(raw, dict):
        raise ContractError("output is required")
    upload_url = raw.get("upload_url")
    object_key = raw.get("object_key")
    content_type = raw.get("content_type")
    headers = raw.get("required_headers") or {}
    if not isinstance(upload_url, str) or urlsplit(upload_url).scheme != "https":
        raise ContractError("output.upload_url must be HTTPS")
    if not isinstance(object_key, str) or not object_key.startswith("projects/") or not object_key.endswith(".webp"):
        raise ContractError("output.object_key must be a versioned projects/.../*.webp key")
    if content_type != OUTPUT_CONTENT_TYPE:
        raise ContractError("output.content_type must be image/webp")
    if not isinstance(headers, dict) or headers.get("Content-Type") != OUTPUT_CONTENT_TYPE:
        raise ContractError("output.required_headers must sign Content-Type: image/webp")
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in headers.items()):
        raise ContractError("output.required_headers must contain strings")
    return OutputTarget(upload_url, object_key, dict(headers))


def _allowed_hosts() -> set[str]:
    return {item.strip().lower() for item in os.environ.get("R2_ALLOWED_DOWNLOAD_HOSTS", "").split(",") if item.strip()}


def download_reference_images(
    urls: object,
    *,
    request_get=requests.get,
    allowed_hosts: set[str] | None = None,
) -> list[dict[str, str]]:
    if not isinstance(urls, list) or not 1 <= len(urls) <= 3 or not all(isinstance(url, str) for url in urls):
        raise ContractError("reference_image_urls must contain one to three HTTPS URLs")
    allowlist = allowed_hosts if allowed_hosts is not None else _allowed_hosts()
    if not allowlist:
        raise ContractError("R2_ALLOWED_DOWNLOAD_HOSTS is not configured")
    prepared = []
    for index, url in enumerate(urls, 1):
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname or parts.hostname.lower() not in allowlist:
            raise ContractError("reference URL host is not allowed")
        try:
            response = request_get(url, timeout=120)
            response.raise_for_status()
            content = response.content
        except requests.RequestException:
            raise RuntimeError("reference image download failed") from None
        if not content or len(content) > MAX_REFERENCE_BYTES:
            raise ContractError("reference image must be between 1 byte and 25 MiB")
        try:
            with Image.open(io.BytesIO(content)) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image = ImageOps.fit(image, (OUTPUT_WIDTH, OUTPUT_HEIGHT), method=Image.Resampling.LANCZOS)
                converted = io.BytesIO()
                image.save(converted, format="PNG")
        except (OSError, ValueError) as exc:
            raise ContractError("reference URL did not return a valid image") from exc
        prepared.append({
            "name": f"catline_reference_{index}.png",
            "image": base64.b64encode(converted.getvalue()).decode("ascii"),
        })
    return prepared


def encode_lossless_webp(image_bytes: bytes) -> tuple[bytes, int, int]:
    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("RGBA")
            if image.size != (OUTPUT_WIDTH, OUTPUT_HEIGHT):
                image = ImageOps.fit(image, (OUTPUT_WIDTH, OUTPUT_HEIGHT), method=Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="WEBP", lossless=True, method=6)
    except (OSError, ValueError) as exc:
        raise ContractError("generated output is not a valid image") from exc
    return output.getvalue(), OUTPUT_WIDTH, OUTPUT_HEIGHT


def upload_generated_image(image_bytes: bytes, raw_target: object, *, request_put=requests.put) -> dict:
    target = validate_output_target(raw_target)
    encoded, width, height = encode_lossless_webp(image_bytes)
    try:
        response = request_put(target.upload_url, data=encoded, headers=target.required_headers, timeout=120)
        response.raise_for_status()
    except requests.RequestException:
        raise RuntimeError("R2 output upload failed") from None
    return {
        "object_key": target.object_key,
        "content_type": OUTPUT_CONTENT_TYPE,
        "size_bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "width": width,
        "height": height,
    }


def models_ready() -> bool:
    marker = os.environ.get("MODEL_READY_MARKER")
    if not marker or not os.path.isfile(marker):
        return False
    if os.environ.get("CATLINE_BUILD_TEST", "").lower() == "true":
        return True
    try:
        manifest = json.loads(Path(os.environ.get("MODEL_MANIFEST_PATH", "/opt/catline/models.json")).read_text())
        model_base = Path(os.environ.get("COMFY_MODEL_BASE", "/runpod-volume/models"))
        return all((model_base / item["target"]).is_file() for item in manifest["files"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False
