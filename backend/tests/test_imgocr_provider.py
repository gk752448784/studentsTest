import pytest

from backend.app.services.ocr import ImgOcrProvider


class FakeImgOcrEngine:
    def __init__(self) -> None:
        self.seen_path: str | None = None

    def ocr(self, image_path: str) -> list[dict]:
        self.seen_path = image_path
        return [
            {"box": [[20, 80], [120, 80], [120, 100], [20, 100]], "text": "第二行", "score": 0.8},
            {"box": [[20, 20], [120, 20], [120, 40], [20, 40]], "text": "第一行", "score": 0.9},
            {"box": [[20, 140], [120, 140], [120, 160], [20, 160]], "text": "", "score": 0.7},
        ]


@pytest.mark.anyio
async def test_imgocr_provider_extracts_sorted_text_from_engine_blocks():
    engine = FakeImgOcrEngine()
    provider = ImgOcrProvider(engine_factory=lambda: engine)

    result = await provider.extract_text(b"fake image bytes", filename="essay.jpg")

    assert result.text == "第一行\n第二行"
    assert result.confidence == pytest.approx(0.85)
    assert engine.seen_path is not None
    assert engine.seen_path.endswith(".jpg")
