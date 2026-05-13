import json

import httpx
import pytest

from backend.app.schemas import EssayCorrectionInput
from backend.app.services.grader import OpenAICompatibleEssayGrader


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.request = httpx.Request("POST", "https://example.test/v1/chat/completions")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request, json=self._payload),
            )
        return None

    def json(self) -> dict:
        return self._payload


class FakeAsyncClient:
    def __init__(self, payload: dict | list[tuple[int, dict]]) -> None:
        self.payload = payload
        self.seen_url: str | None = None
        self.seen_headers: dict | None = None
        self.seen_json: dict | None = None
        self.post_count = 0

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    async def post(self, url: str, headers: dict, json: dict) -> FakeResponse:
        self.seen_url = url
        self.seen_headers = headers
        self.seen_json = json
        self.post_count += 1
        if isinstance(self.payload, list):
            status_code, payload = self.payload.pop(0)
            return FakeResponse(payload, status_code=status_code)
        return FakeResponse(self.payload)


@pytest.mark.anyio
async def test_openai_compatible_grader_posts_chat_completion_and_parses_json():
    model_content = {
        "score": {
            "total": 88,
            "content": 19,
            "structure": 17,
            "language": 18,
            "mechanics": 16,
            "presentation": 18,
        },
        "comments": {
            "summary": "这篇《我爱四季》层次清楚，语言较丰富。",
            "strengths": ["引用诗句丰富", "四季结构清晰"],
            "issues": ["个别句子略长"],
            "suggestions": ["可以补充自己的真实感受"],
            "encouragement": "继续保持积累和观察。",
            "spellingIssues": ["未发现明显错别字。"],
            "sentenceIssues": ["有些句子可以拆短。"],
            "revisionExample": "我爱四季，因为每个季节都有不同的美。",
            "teacherNotes": "重点引导学生补充自己的观察和感受。",
        },
    }
    fake_client = FakeAsyncClient(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(model_content, ensure_ascii=False),
                    }
                }
            ]
        }
    )
    grader = OpenAICompatibleEssayGrader(
        base_url="https://example.test",
        api_key="test-key",
        model="test-model",
        http_client_factory=lambda: fake_client,
    )

    result = await grader.grade(
        essay_text="四季\n我爱春天，也爱夏天。",
        correction_input=EssayCorrectionInput(
            title="我爱四季",
            requirements="围绕四季特点写清楚内容。",
            grade_level="小学三年级",
            essay_type="命题作文",
        ),
    )

    assert result.score.total == 88
    assert result.comments.summary == "这篇《我爱四季》层次清楚，语言较丰富。"
    assert result.comments.spelling_issues == ["未发现明显错别字。"]
    assert result.comments.sentence_issues == ["有些句子可以拆短。"]
    assert result.comments.revision_example == "我爱四季，因为每个季节都有不同的美。"
    assert result.comments.teacher_notes == "重点引导学生补充自己的观察和感受。"
    assert fake_client.seen_url == "https://example.test/v1/chat/completions"
    assert fake_client.seen_headers == {"Authorization": "Bearer test-key"}
    assert fake_client.seen_json is not None
    assert fake_client.seen_json["model"] == "test-model"
    assert fake_client.seen_json["response_format"] == {"type": "json_object"}
    user_message = fake_client.seen_json["messages"][1]["content"]
    assert "我爱四季" in user_message
    assert "四季\n我爱春天" in user_message


@pytest.mark.anyio
async def test_openai_compatible_grader_extracts_json_from_markdown_fence():
    fake_client = FakeAsyncClient(
        {
            "choices": [
                {
                    "message": {
                        "content": """```json
{"score":{"total":80,"content":16,"structure":16,"language":16,"mechanics":16,"presentation":16},"comments":{"summary":"整体完成。","strengths":["内容完整"],"issues":["细节不足"],"suggestions":["增加细节"],"encouragement":"继续加油。","spellingIssues":["无明显错别字。"],"sentenceIssues":["句子偏短。"],"revisionExample":"把看到的景物写具体。","teacherNotes":"鼓励学生补充细节。"}}
```""",
                    }
                }
            ]
        }
    )
    grader = OpenAICompatibleEssayGrader(
        base_url="https://example.test/v1",
        api_key="test-key",
        model="test-model",
        http_client_factory=lambda: fake_client,
    )

    result = await grader.grade(
        essay_text="作文文本",
        correction_input=EssayCorrectionInput(title="题目"),
    )

    assert result.score.total == 80
    assert result.comments.suggestions == ["增加细节"]
    assert fake_client.seen_url == "https://example.test/v1/chat/completions"


@pytest.mark.anyio
async def test_openai_compatible_grader_retries_temporary_upstream_errors():
    model_content = {
        "score": {
            "total": 86,
            "content": 18,
            "structure": 17,
            "language": 17,
            "mechanics": 17,
            "presentation": 17,
        },
        "comments": {
            "summary": "整体完成较好。",
            "strengths": ["结构清楚"],
            "issues": ["感受可以更具体"],
            "suggestions": ["补充自己的观察"],
            "encouragement": "继续保持。",
            "spellingIssues": ["无明显错别字。"],
            "sentenceIssues": ["个别句子可再通顺。"],
            "revisionExample": "把四季的特点和自己的感受连起来写。",
            "teacherNotes": "上游短暂失败后重试成功。",
        },
    }
    fake_client = FakeAsyncClient(
        [
            (503, {"error": "Service Unavailable"}),
            (
                200,
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(model_content, ensure_ascii=False),
                            }
                        }
                    ]
                },
            ),
        ]
    )
    grader = OpenAICompatibleEssayGrader(
        base_url="https://example.test",
        api_key="test-key",
        model="test-model",
        http_client_factory=lambda: fake_client,
    )

    result = await grader.grade(
        essay_text="四季\n我爱春天，也爱夏天。",
        correction_input=EssayCorrectionInput(title="我爱四季"),
    )

    assert result.score.total == 86
    assert fake_client.post_count == 2
