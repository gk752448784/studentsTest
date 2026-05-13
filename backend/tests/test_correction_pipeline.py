import pytest

from backend.app.schemas import EssayCorrectionInput
from backend.app.services.correction_pipeline import CorrectionPipeline
from backend.app.services.grader import DeterministicEssayGrader
from backend.app.services.ocr import MockOcrProvider


@pytest.mark.anyio
async def test_correction_pipeline_combines_ocr_text_with_grading_result():
    pipeline = CorrectionPipeline(
        ocr_provider=MockOcrProvider(),
        grader=DeterministicEssayGrader(),
    )

    result = await pipeline.correct(
        image_bytes=b"fake image bytes",
        filename="essay.jpg",
        correction_input=EssayCorrectionInput(
            title="一次难忘的春游",
            requirements="写清楚事情经过。",
            grade_level="小学三年级",
            essay_type="命题作文",
        ),
    )

    assert result.id.startswith("corr_")
    assert result.status == "completed"
    assert "春游" in result.ocr_text
    assert result.score.total == 82
    assert "一次难忘的春游" in result.comments.summary
    assert result.comments.spelling_issues
    assert result.comments.sentence_issues
    assert result.comments.revision_example
    assert result.comments.teacher_notes


@pytest.mark.anyio
async def test_correction_pipeline_does_not_hardcode_spring_outing_feedback():
    pipeline = CorrectionPipeline(
        ocr_provider=MockOcrProvider(),
        grader=DeterministicEssayGrader(),
    )

    result = await pipeline.correct(
        image_bytes=b"fake image bytes",
        filename="essay.jpg",
        correction_input=EssayCorrectionInput(
            title="我爱四季",
            requirements="围绕四季特点写清楚内容。",
            grade_level="小学三年级",
            essay_type="命题作文",
        ),
    )

    all_comments = "\n".join(
        [
            result.comments.summary,
            *result.comments.strengths,
            *result.comments.issues,
            *result.comments.suggestions,
            result.comments.encouragement,
            *result.comments.spelling_issues,
            *result.comments.sentence_issues,
            result.comments.revision_example,
            result.comments.teacher_notes,
        ]
    )
    assert "我爱四季" in result.comments.summary
    assert "春游" not in all_comments
    assert "同学做游戏" not in all_comments
