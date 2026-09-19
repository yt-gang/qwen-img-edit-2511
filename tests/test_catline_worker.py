from __future__ import annotations

import io

import pytest
import requests
from PIL import Image

from catline_worker import (
    ContractError,
    download_reference_images,
    upload_generated_image,
)


class Response:
    def __init__(self, content=b""):
        self.content = content

    def raise_for_status(self):
        return None


def png_bytes():
    output = io.BytesIO()
    Image.new("RGB", (32, 48), "blue").save(output, "PNG")
    return output.getvalue()


def test_downloads_only_allowlisted_https_references():
    refs = download_reference_images(
        ["https://r2.example.test/ref?signature=secret"],
        allowed_hosts={"r2.example.test"},
        request_get=lambda *args, **kwargs: Response(png_bytes()),
    )
    assert refs[0]["name"] == "catline_reference_1.png"
    with pytest.raises(ContractError):
        download_reference_images(
            ["https://evil.example/ref"], allowed_hosts={"r2.example.test"},
            request_get=lambda *args, **kwargs: Response(png_bytes()),
        )


def test_uploads_webp_without_returning_signed_url():
    captured = {}
    target = {
        "upload_url": "https://r2.example.test/out?signature=secret",
        "object_key": "projects/p/scenes/s/images/v2.webp",
        "content_type": "image/webp",
        "required_headers": {"Content-Type": "image/webp"},
    }

    def put(url, *, data, headers, timeout):
        captured["data"] = data
        return Response()

    asset = upload_generated_image(png_bytes(), target, request_put=put)
    assert "upload_url" not in asset
    with Image.open(io.BytesIO(captured["data"])) as image:
        assert image.format == "WEBP" and image.size == (1080, 1920)


def test_reference_download_error_redacts_signed_url():
    def fail(*args, **kwargs):
        raise requests.ConnectionError("https://r2.example.test/ref?secret=do-not-log")

    with pytest.raises(RuntimeError, match="reference image download failed") as raised:
        download_reference_images(
            ["https://r2.example.test/ref?secret=do-not-log"],
            allowed_hosts={"r2.example.test"}, request_get=fail,
        )
    assert "do-not-log" not in str(raised.value)
