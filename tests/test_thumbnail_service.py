import sys
import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.legal_thumbnail_service import InfraiClient, InfraiError, MatterImage, create_matter_thumbnail


class FakeClient:
    def upload(self, image):
        return {"image": "uploaded-image-id"}

    def process_thumbnail(self, image, key):
        assert image == "uploaded-image-id"
        assert key.startswith("matters/case-42/")
        return {"url": "https://cdn.example/thumb.webp"}


def test_thumbnail_keeps_matter_workflow_visible():
    result = create_matter_thumbnail(MatterImage("data", "signed.pdf", "case-42", "signed_delivery"), FakeClient())
    assert result["matter_id"] == "case-42"
    assert result["document_kind"] == "signed_delivery"
    assert result["thumbnail"]["url"].endswith("thumb.webp")


def test_unknown_workflow_is_rejected():
    with pytest.raises(ValueError):
        create_matter_thumbnail(MatterImage("data", "x", "case-42", "other"), FakeClient())


def test_process_uses_pipeline_contract():
    class Response:
        status = 200
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def read(self):
            return b'{"ok":true,"data":{"url":"thumbnail"}}'

    def opener(req, timeout):
        body = json.loads(req.data)
        assert set(body) == {"image", "ops", "format", "store"}
        assert body["image"] == {"image_id": "image-id"}
        assert body["ops"] == [{"op": "resize", "params": {"width": 640, "height": 360, "fit": "cover"}}]
        assert body["store"] is False
        return Response()

    assert InfraiClient("key", opener).process_thumbnail("image-id", "key") == {"url": "thumbnail"}


def test_http_400_envelope_is_not_retried():
    calls = []

    def opener(req, timeout):
        calls.append(req)
        raise HTTPError(req.full_url, 400, "Bad Request", {}, io.BytesIO(b'{"ok":false,"error":{"code":"INVALID_PARAM"}}'))

    with pytest.raises(InfraiError) as exc:
        InfraiClient("key", opener).process_thumbnail("image-id", "key")
    assert exc.value.code == "INVALID_PARAM"
    assert len(calls) == 1
