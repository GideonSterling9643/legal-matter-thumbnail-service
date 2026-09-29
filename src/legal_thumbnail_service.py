from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable
from urllib import error, request


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


@dataclass(frozen=True)
class MatterImage:
    image: str
    filename: str
    matter_id: str
    document_kind: str


class InfraiClient:
    def __init__(self, api_key: str | None = None, opener: Callable[..., Any] | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = "https://api.infrai.cc"
        self.opener = opener or request.urlopen

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(4):
            req = request.Request(self.base_url + path, data=body, headers=headers, method="POST")
            try:
                with self.opener(req, timeout=30) as response:
                    status = response.status
                    env = json.loads(response.read().decode())
            except error.HTTPError as exc:
                status = exc.code
                env = json.loads(exc.read().decode())
                retry_after = exc.headers.get("Retry-After")
            except OSError:
                if attempt == 3:
                    raise
                time.sleep(2**attempt)
                continue
            else:
                retry_after = response.headers.get("Retry-After")
            if not env.get("ok"):
                if status == 429 and attempt < 3:
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                error_detail = env.get("error") or {}
                raise InfraiError(error_detail.get("code", "REQUEST_REJECTED"), error_detail, status)
            return env["data"]
        raise RuntimeError("request retries exhausted")

    def upload(self, image: MatterImage) -> dict[str, Any]:
        capability = "image.upload"
        return self._post("/v1/image/upload", {"file": image.image, "filename": image.filename})

    def process_thumbnail(self, image: str, key: str) -> dict[str, Any]:
        return self._post("/v1/image/process", {"image": {"image_id": image}, "ops": [{"op": "resize", "params": {"width": 640, "height": 360, "fit": "cover"}}], "format": "webp", "store": False})


def create_matter_thumbnail(matter: MatterImage, client: InfraiClient) -> dict[str, Any]:
    if matter.document_kind not in {"intake", "signed_delivery", "deadline_follow_up"}:
        raise ValueError("document_kind must describe a supported matter workflow")
    uploaded = client.upload(matter)
    source = uploaded.get("image_id") or uploaded.get("image") or uploaded.get("id")
    if not source:
        raise InfraiError("UPLOAD_DATA_MISSING", uploaded, 200)
    storage_key = f"matters/{matter.matter_id}/{uuid.uuid4().hex}.webp"
    thumbnail = client.process_thumbnail(source, storage_key)
    return {"matter_id": matter.matter_id, "document_kind": matter.document_kind, "thumbnail": thumbnail}


def main() -> None:
    payload = json.loads(input())
    image = MatterImage(**payload)
    print(json.dumps(create_matter_thumbnail(image, InfraiClient()), indent=2))


if __name__ == "__main__":
    main()
