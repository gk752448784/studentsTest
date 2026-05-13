import base64
import json
from email.utils import parsedate_to_datetime

import pytest

from backend.app.services.ocr import XfyunOcrProvider


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class FakeAsyncClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.seen_url: str | None = None
        self.seen_json: dict | None = None

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    async def post(self, url: str, json: dict) -> FakeResponse:
        self.seen_url = url
        self.seen_json = json
        return FakeResponse(self.payload)


@pytest.mark.anyio
async def test_xfyun_ocr_provider_builds_signed_request_and_decodes_plain_text():
    response_text = base64.b64encode("我爱春天\n春天真美".encode("utf-8")).decode("utf-8")
    fake_client = FakeAsyncClient(
        {
            "header": {"code": 0, "message": "success"},
            "payload": {"result": {"text": response_text}},
        }
    )
    provider = XfyunOcrProvider(
        app_id="appid",
        api_key="apikey",
        api_secret="apisecret",
        http_client_factory=lambda: fake_client,
        date_factory=lambda: parsedate_to_datetime("Wed, 11 Aug 2021 06:55:18 GMT"),
    )

    result = await provider.extract_text(b"fake image bytes", filename="essay.png")

    assert result.text == "我爱春天\n春天真美"
    assert result.confidence == 1.0
    assert fake_client.seen_url is not None
    assert "authorization=" in fake_client.seen_url
    assert "date=Wed%2C+11+Aug+2021+06%3A55%3A18+GMT" in fake_client.seen_url
    assert fake_client.seen_json is not None
    assert fake_client.seen_json["header"]["app_id"] == "appid"
    assert fake_client.seen_json["payload"]["image"]["encoding"] == "png"
    assert fake_client.seen_json["payload"]["image"]["image"] == base64.b64encode(
        b"fake image bytes"
    ).decode("utf-8")


@pytest.mark.anyio
async def test_xfyun_ocr_provider_extracts_markdown_from_decoded_json_result():
    decoded_payload = {"markdown": "# 作文\n我爱夏天。", "pages": []}
    response_text = base64.b64encode(
        json.dumps(decoded_payload, ensure_ascii=False).encode("utf-8")
    ).decode("utf-8")
    fake_client = FakeAsyncClient(
        {
            "header": {"code": 0, "message": "success"},
            "payload": {"result": {"text": response_text}},
        }
    )
    provider = XfyunOcrProvider(
        app_id="appid",
        api_key="apikey",
        api_secret="apisecret",
        http_client_factory=lambda: fake_client,
    )

    result = await provider.extract_text(b"fake image bytes", filename="essay.jpg")

    assert result.text == "# 作文\n我爱夏天。"


@pytest.mark.anyio
async def test_xfyun_ocr_provider_raises_when_xfyun_returns_error_code():
    fake_client = FakeAsyncClient({"header": {"code": 11200, "message": "auth no license"}})
    provider = XfyunOcrProvider(
        app_id="appid",
        api_key="apikey",
        api_secret="apisecret",
        http_client_factory=lambda: fake_client,
    )

    with pytest.raises(RuntimeError, match="auth no license"):
        await provider.extract_text(b"fake image bytes", filename="essay.jpg")
