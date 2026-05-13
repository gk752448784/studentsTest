from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.app.core.config import Settings, get_settings
from backend.app.schemas import EssayCorrectionInput, EssayCorrectionResponse
from backend.app.services.correction_pipeline import CorrectionPipeline
from backend.app.services.provider_factory import build_correction_pipeline
from backend.app.services.template_store import template_store

router = APIRouter(prefix="/essay-corrections", tags=["essay-corrections"])


async def get_pipeline(settings: Settings = Depends(get_settings)) -> CorrectionPipeline:
    return build_correction_pipeline(settings)


@router.post("", response_model=EssayCorrectionResponse)
async def create_essay_correction(
    template_id: str | None = Form(default=None),
    title: str | None = Form(default=None),
    requirements: str = Form(default=""),
    grade_level: str = Form(default="小学三年级"),
    essay_type: str = Form(default="命题作文"),
    image: UploadFile = File(...),
    pipeline: CorrectionPipeline = Depends(get_pipeline),
) -> EssayCorrectionResponse:
    image_bytes = await image.read()
    if template_id:
        correction_input = template_store.to_correction_input(template_id)
        if correction_input is None:
            raise HTTPException(status_code=404, detail="Essay template not found")
    else:
        if not title:
            raise HTTPException(status_code=422, detail="Either template_id or title is required")
        correction_input = EssayCorrectionInput(
            title=title,
            requirements=requirements,
            grade_level=grade_level,
            essay_type=essay_type,
        )
    correction = await pipeline.correct(
        image_bytes=image_bytes,
        filename=image.filename,
        correction_input=correction_input,
    )
    return template_store.save_correction(correction)


@router.get("/{correction_id}", response_model=EssayCorrectionResponse)
async def get_essay_correction(correction_id: str) -> EssayCorrectionResponse:
    correction = template_store.get_correction(correction_id)
    if correction is None:
        raise HTTPException(status_code=404, detail="Essay correction not found")
    return correction
