import base64
import gzip
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable
from typing import Protocol
from urllib.parse import urlencode, urlparse

import httpx


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float


class OcrProvider(Protocol):
    async def extract_text(self, image_bytes: bytes, filename: str | None = None) -> OcrResult:
        """Extract essay text from uploaded image bytes."""


class MockOcrProvider:
    async def extract_text(self, image_bytes: bytes, filename: str | None = None) -> OcrResult:
        return OcrResult(
            text=(
                "今天我们去春游。早上我和同学们坐车来到公园，"
                "看见了绿绿的小草和美丽的花。我们一起做游戏，还分享了零食。"
                "这次春游让我很开心，我希望下次还能和大家一起去。"
            ),
            confidence=0.86,
        )


class ImgOcrProvider:
    def __init__(self, engine_factory: Callable[[], object] | None = None) -> None:
        self._engine_factory = engine_factory or self._default_engine_factory
        self._engine: object | None = None

    async def extract_text(self, image_bytes: bytes, filename: str | None = None) -> OcrResult:
        suffix = Path(filename or "essay.jpg").suffix or ".jpg"
        with NamedTemporaryFile(suffix=suffix) as image_file:
            image_file.write(image_bytes)
            image_file.flush()
            blocks = self._run_ocr(image_file.name)
        return self._to_result(blocks)

    def _run_ocr(self, image_path: str) -> list[dict]:
        engine = self._get_engine()
        ocr_method = getattr(engine, "ocr")
        result = ocr_method(image_path)
        if not isinstance(result, list):
            raise TypeError("imgocr result must be a list of OCR blocks")
        return result

    def _get_engine(self) -> object:
        if self._engine is None:
            self._engine = self._engine_factory()
        return self._engine

    @staticmethod
    def _default_engine_factory() -> object:
        try:
            from imgocr import ImgOcr
        except ImportError as exc:
            raise RuntimeError(
                "imgocr provider requires optional OCR dependencies. "
                "Install with: uv sync --extra dev --extra ocr"
            ) from exc

        return ImgOcr(use_gpu=False, is_efficiency_mode=False)

    @staticmethod
    def _to_result(blocks: list[dict]) -> OcrResult:
        non_empty_blocks = [
            block for block in blocks if str(block.get("text", "")).strip()
        ]
        sorted_blocks = sorted(non_empty_blocks, key=ImgOcrProvider._block_sort_key)
        text = "\n".join(str(block["text"]).strip() for block in sorted_blocks)
        if not sorted_blocks:
            return OcrResult(text="", confidence=0.0)
        confidence = sum(float(block.get("score", 0.0)) for block in sorted_blocks) / len(sorted_blocks)
        return OcrResult(text=text, confidence=confidence)

    @staticmethod
    def _block_sort_key(block: dict) -> tuple[float, float]:
        box = block.get("box") or [[0, 0]]
        first_point = box[0] if box else [0, 0]
        x = float(first_point[0]) if len(first_point) > 0 else 0.0
        y = float(first_point[1]) if len(first_point) > 1 else 0.0
        return (y, x)


class XfyunOcrProvider:
    def __init__(
        self,
        app_id: str,
        api_key: str,
        api_secret: str,
        endpoint: str = "https://cbm01.cn-huabei-1.xf-yun.com/v1/private/se75ocrbm",
        http_client_factory: Callable[[], Any] | None = None,
        date_factory: Callable[[], datetime] | None = None,
    ) -> None:
        if not app_id or not api_key or not api_secret:
            raise ValueError("Xfyun OCR requires app_id, api_key, and api_secret")

        self._app_id = app_id
        self._api_key = api_key
        self._api_secret = api_secret
        self._endpoint = endpoint
        self._http_client_factory = http_client_factory or self._default_http_client_factory
        self._date_factory = date_factory or (lambda: datetime.now(timezone.utc))

    async def extract_text(self, image_bytes: bytes, filename: str | None = None) -> OcrResult:
        request_url = self._build_signed_url()
        request_body = self._build_request_body(image_bytes, filename)
        async with self._http_client_factory() as client:
            response = await client.post(request_url, json=request_body)
            response.raise_for_status()
            response_json = response.json()
        return self._parse_response(response_json)

    def _build_signed_url(self) -> str:
        parsed = urlparse(self._endpoint)
        host = parsed.netloc
        request_line = f"POST {parsed.path} HTTP/1.1"
        date = format_datetime(self._date_factory().astimezone(timezone.utc), usegmt=True)
        signature_origin = f"host: {host}\ndate: {date}\n{request_line}"
        signature_sha = hmac.new(
            self._api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")
        authorization_origin = (
            f'api_key="{self._api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
        query = urlencode({"authorization": authorization, "host": host, "date": date})
        return f"{self._endpoint}?{query}"

    def _build_request_body(self, image_bytes: bytes, filename: str | None) -> dict[str, Any]:
        return {
            "header": {
                "app_id": self._app_id,
                "status": 0,
            },
            "parameter": {
                "ocr": {
                    "result_option": "normal",
                    "result_format": "json,markdown",
                    "output_type": "one_shot",
                    "exif_option": "0",
                    "markdown_element_option": "watermark=0,page_header=0,page_footer=0,page_number=0,graph=0",
                    "sed_element_option": "watermark=0,page_header=0,page_footer=0,page_number=0,graph=0",
                    "alpha_option": "0",
                    "rotation_min_angle": 5,
                    "result": {
                        "encoding": "utf8",
                        "compress": "raw",
                        "format": "plain",
                    },
                }
            },
            "payload": {
                "image": {
                    "encoding": self._image_encoding(filename),
                    "image": base64.b64encode(image_bytes).decode("utf-8"),
                    "status": 0,
                    "seq": 0,
                }
            },
        }

    @staticmethod
    def _image_encoding(filename: str | None) -> str:
        suffix = Path(filename or "essay.jpg").suffix.lower().lstrip(".")
        if suffix == "jpeg":
            return "jpg"
        if suffix in {"jpg", "png", "bmp"}:
            return suffix
        return "jpg"

    @staticmethod
    def _parse_response(response_json: dict[str, Any]) -> OcrResult:
        header = response_json.get("header", {})
        code = int(header.get("code", 0))
        if code != 0:
            message = header.get("message", "Xfyun OCR request failed")
            raise RuntimeError(f"Xfyun OCR error {code}: {message}")

        result = response_json.get("payload", {}).get("result", {})
        encoded_text = result.get("text", "")
        if not encoded_text:
            return OcrResult(text="", confidence=0.0)
        decoded_bytes = base64.b64decode(encoded_text)
        if result.get("compress") == "gzip":
            decoded_bytes = gzip.decompress(decoded_bytes)
        decoded_text = decoded_bytes.decode(result.get("encoding", "utf8"))
        normalized_text = XfyunOcrProvider._normalize_decoded_text(decoded_text)
        return OcrResult(text=normalized_text, confidence=1.0)

    @staticmethod
    def _normalize_decoded_text(decoded_text: str) -> str:
        try:
            decoded_json = json.loads(decoded_text)
        except json.JSONDecodeError:
            return decoded_text.strip()

        markdown = XfyunOcrProvider._find_first_string(decoded_json, {"markdown", "md"})
        if markdown:
            return markdown.strip()

        collected_text = XfyunOcrProvider._collect_text_values(decoded_json)
        return "\n".join(collected_text).strip()

    @staticmethod
    def _find_first_string(value: Any, keys: set[str]) -> str | None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in keys and isinstance(item, str) and item.strip():
                    return item
            for item in value.values():
                found = XfyunOcrProvider._find_first_string(item, keys)
                if found:
                    return found
        if isinstance(value, list):
            for item in value:
                found = XfyunOcrProvider._find_first_string(item, keys)
                if found:
                    return found
        return None

    @staticmethod
    def _collect_text_values(value: Any) -> list[str]:
        if isinstance(value, dict):
            values: list[str] = []
            for key, item in value.items():
                if key in {"text", "content"} and isinstance(item, str) and item.strip():
                    values.append(item.strip())
                else:
                    values.extend(XfyunOcrProvider._collect_text_values(item))
            return values
        if isinstance(value, list):
            values: list[str] = []
            for item in value:
                values.extend(XfyunOcrProvider._collect_text_values(item))
            return values
        return []

    @staticmethod
    def _default_http_client_factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=60.0, trust_env=False)
