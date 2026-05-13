import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


@pytest.mark.anyio
async def test_create_essay_correction_from_uploaded_image_returns_structured_feedback():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/essay-corrections",
            data={
                "title": "一次难忘的春游",
                "requirements": "围绕春游经历写清楚事情经过，语句通顺，有真情实感。",
                "grade_level": "小学三年级",
                "essay_type": "命题作文",
            },
            files={
                "image": (
                    "essay.jpg",
                    b"fake image bytes",
                    "image/jpeg",
                )
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["id"].startswith("corr_")
    assert body["status"] == "completed"
    assert body["ocrText"]
    assert body["score"]["total"] == 82
    assert body["score"]["content"] == 18
    assert body["score"]["structure"] == 16
    assert body["score"]["language"] == 17
    assert body["score"]["mechanics"] == 15
    assert body["score"]["presentation"] == 16
    assert "春游" in body["comments"]["summary"]
    assert body["comments"]["strengths"]
    assert body["comments"]["issues"]
    assert body["comments"]["suggestions"]
    assert body["comments"]["encouragement"]
    assert body["comments"]["spellingIssues"]
    assert body["comments"]["sentenceIssues"]
    assert body["comments"]["revisionExample"]
    assert body["comments"]["teacherNotes"]


@pytest.mark.anyio
async def test_create_essay_correction_persists_result_for_later_lookup():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        create_response = await client.post(
            "/api/v1/essay-corrections",
            data={
                "title": "我爱四季",
                "requirements": "围绕四季特点写清楚内容。",
                "grade_level": "小学三年级",
                "essay_type": "命题作文",
            },
            files={"image": ("essay.jpg", b"fake image bytes", "image/jpeg")},
        )
        correction_id = create_response.json()["id"]

        lookup_response = await client.get(f"/api/v1/essay-corrections/{correction_id}")

    assert lookup_response.status_code == 200
    assert lookup_response.json() == create_response.json()


@pytest.mark.anyio
async def test_get_essay_correction_returns_404_for_unknown_id():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/essay-corrections/corr_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Essay correction not found"




@pytest.mark.anyio
async def test_create_essay_correction_rejects_missing_image():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/essay-corrections",
            data={
                "title": "我的妈妈",
                "requirements": "写清楚人物特点。",
                "grade_level": "小学三年级",
                "essay_type": "命题作文",
            },
        )

    assert response.status_code == 422
