from fastapi import APIRouter

from backend.app.schemas import EssayTemplate, EssayTemplateCreate, EssayTemplateList
from backend.app.services.template_store import template_store

router = APIRouter(prefix="/essay-templates", tags=["essay-templates"])


@router.post("", response_model=EssayTemplate)
async def create_essay_template(template: EssayTemplateCreate) -> EssayTemplate:
    return template_store.create(template)


@router.get("", response_model=EssayTemplateList)
async def list_essay_templates() -> EssayTemplateList:
    return EssayTemplateList(items=template_store.list())
