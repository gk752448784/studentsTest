import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.schemas import EssayTemplateCreate
from backend.app.services.template_store import SQLiteEssayStore
from backend.app.services.template_store import template_store


@pytest.fixture(autouse=True)
def clear_templates():
    template_store.clear()


@pytest.mark.anyio
async def test_create_essay_template_returns_template_id():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/essay-templates",
            json={
                "title": "一次难忘的春游",
                "requirements": "写清楚事情经过，语句通顺，有真情实感。",
                "grade_level": "小学三年级",
                "essay_type": "命题作文",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["id"].startswith("tpl_")
    assert body["title"] == "一次难忘的春游"
    assert body["requirements"] == "写清楚事情经过，语句通顺，有真情实感。"
    assert body["grade_level"] == "小学三年级"
    assert body["essay_type"] == "命题作文"


@pytest.mark.anyio
async def test_create_essay_correction_uses_template_id_for_context():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        template_response = await client.post(
            "/api/v1/essay-templates",
            json={
                "title": "我喜欢的一本书",
                "requirements": "写出书名、主要内容和自己的感受。",
                "grade_level": "小学四年级",
                "essay_type": "读后感",
            },
        )
        template_id = template_response.json()["id"]

        response = await client.post(
            "/api/v1/essay-corrections",
            data={"template_id": template_id},
            files={"image": ("essay.jpg", b"fake image bytes", "image/jpeg")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert "我喜欢的一本书" in body["comments"]["summary"]
    assert body["ocrText"]


@pytest.mark.anyio
async def test_create_essay_correction_rejects_unknown_template_id():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/essay-corrections",
            data={"template_id": "tpl_missing"},
            files={"image": ("essay.jpg", b"fake image bytes", "image/jpeg")},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Essay template not found"


def test_sqlite_essay_store_persists_templates_between_instances(tmp_path):
    db_path = tmp_path / "essay.sqlite3"
    first_store = SQLiteEssayStore(db_path=db_path)

    created = first_store.create(
        EssayTemplateCreate(
            title="我爱四季",
            requirements="围绕四季特点写清楚内容。",
            grade_level="小学三年级",
            essay_type="命题作文",
        )
    )

    second_store = SQLiteEssayStore(db_path=db_path)
    restored = second_store.get(created.id)

    assert restored == created
    assert second_store.to_correction_input(created.id) is not None
