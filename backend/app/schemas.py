from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EssayCorrectionInput(BaseModel):
    title: str
    requirements: str = ""
    grade_level: str = Field(default="小学三年级")
    essay_type: str = Field(default="命题作文")


class EssayTemplateCreate(EssayCorrectionInput):
    pass


class EssayTemplate(EssayTemplateCreate):
    id: str


class EssayTemplateList(BaseModel):
    items: list[EssayTemplate]


class EssayScore(BaseModel):
    total: int
    content: int
    structure: int
    language: int
    mechanics: int
    presentation: int


class EssayComments(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    summary: str
    strengths: list[str]
    issues: list[str]
    suggestions: list[str]
    encouragement: str
    spelling_issues: list[str] = Field(
        default_factory=list,
        serialization_alias="spellingIssues",
        validation_alias="spellingIssues",
    )
    sentence_issues: list[str] = Field(
        default_factory=list,
        serialization_alias="sentenceIssues",
        validation_alias="sentenceIssues",
    )
    revision_example: str = Field(
        default="",
        serialization_alias="revisionExample",
        validation_alias="revisionExample",
    )
    teacher_notes: str = Field(
        default="",
        serialization_alias="teacherNotes",
        validation_alias="teacherNotes",
    )


class EssayCorrectionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    status: Literal["completed"]
    ocr_text: str = Field(serialization_alias="ocrText", validation_alias="ocrText")
    score: EssayScore
    comments: EssayComments
