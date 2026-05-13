from backend.app.core.config import Settings
from backend.app.services.correction_pipeline import CorrectionPipeline
from backend.app.services.grader import (
    DeterministicEssayGrader,
    EssayGrader,
    OpenAICompatibleEssayGrader,
)
from backend.app.services.ocr import ImgOcrProvider, MockOcrProvider, OcrProvider, XfyunOcrProvider


def build_correction_pipeline(settings: Settings) -> CorrectionPipeline:
    return CorrectionPipeline(
        ocr_provider=_build_ocr_provider(settings),
        grader=_build_grader(settings),
    )


def _build_ocr_provider(settings: Settings) -> OcrProvider:
    provider_name = settings.ocr_provider
    if provider_name == "mock":
        return MockOcrProvider()
    if provider_name == "imgocr":
        return ImgOcrProvider()
    if provider_name == "xfyun_ocr":
        return XfyunOcrProvider(
            app_id=settings.xfyun_app_id,
            api_key=settings.xfyun_api_key,
            api_secret=settings.xfyun_api_secret,
            endpoint=settings.xfyun_endpoint,
        )
    raise ValueError(f"Unsupported OCR provider: {provider_name}")


def _build_grader(settings: Settings) -> EssayGrader:
    provider_name = settings.grader_provider
    if provider_name == "deterministic":
        return DeterministicEssayGrader()
    if provider_name == "openai_compatible":
        return OpenAICompatibleEssayGrader(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )
    raise ValueError(f"Unsupported grader provider: {provider_name}")
