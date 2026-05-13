from uuid import uuid4

from backend.app.schemas import EssayCorrectionInput, EssayCorrectionResponse
from backend.app.services.grader import EssayGrader
from backend.app.services.ocr import OcrProvider


class CorrectionPipeline:
    def __init__(self, ocr_provider: OcrProvider, grader: EssayGrader) -> None:
        self._ocr_provider = ocr_provider
        self._grader = grader

    async def correct(
        self,
        image_bytes: bytes,
        filename: str | None,
        correction_input: EssayCorrectionInput,
    ) -> EssayCorrectionResponse:
        ocr_result = await self._ocr_provider.extract_text(image_bytes, filename)
        grading_result = await self._grader.grade(ocr_result.text, correction_input)

        return EssayCorrectionResponse(
            id=f"corr_{uuid4().hex}",
            status="completed",
            ocr_text=ocr_result.text,
            score=grading_result.score,
            comments=grading_result.comments,
        )
