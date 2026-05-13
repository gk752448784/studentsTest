import json
from dataclasses import dataclass
from typing import Any, Callable, Protocol

import httpx

from backend.app.schemas import EssayComments, EssayCorrectionInput, EssayScore


@dataclass(frozen=True)
class GradingResult:
    score: EssayScore
    comments: EssayComments


class EssayGrader(Protocol):
    async def grade(self, essay_text: str, correction_input: EssayCorrectionInput) -> GradingResult:
        """Grade OCR text using the supplied elementary-school writing context."""


class EssayGraderError(RuntimeError):
    """Raised when the configured essay grading provider cannot return a result."""


class DeterministicEssayGrader:
    async def grade(self, essay_text: str, correction_input: EssayCorrectionInput) -> GradingResult:
        title_hint = correction_input.title or "作文题目"
        score = EssayScore(
            total=82,
            content=18,
            structure=16,
            language=17,
            mechanics=15,
            presentation=16,
        )
        comments = EssayComments(
            summary=(
                f"这篇《{title_hint}》能围绕题目展开，事情经过比较清楚，"
                "也写出了自己的心情。后续可以再增加看到、听到和想到的细节，"
                "让内容更具体。"
            ),
            strengths=[
                "能按时间顺序写出事情经过，读起来比较清楚。",
                "结尾能表达自己的心情，有真实感受。",
            ],
            issues=[
                "部分句子偏简单，画面描写还可以更丰富。",
                "需要继续注意错别字、标点和句子停顿。",
            ],
            suggestions=[
                "补充一两个具体场景，比如看到的景物、人物动作或当时的感受。",
                "把概括性的心情词换成更具体的表现，例如动作、语言或心理活动。",
            ],
            encouragement="整体完成度不错，继续保持观察生活的习惯，下次可以写得更生动。",
            spelling_issues=[
                "未发现明显连续错别字，正式批改时可以结合 OCR 原图逐字复核。",
            ],
            sentence_issues=[
                "有些句子还可以写得更具体，避免只用概括性的形容词。",
            ],
            revision_example=(
                f"我喜欢《{title_hint}》中的一个具体片段，因为它让我看到、听到，"
                "也感受到当时的心情。"
            ),
            teacher_notes="建议重点看内容是否扣题、细节是否具体，再检查错别字和标点。",
        )
        return GradingResult(score=score, comments=comments)


class OpenAICompatibleEssayGrader:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        http_client_factory: Callable[[], Any] | None = None,
    ) -> None:
        if not base_url or not api_key or not model:
            raise ValueError("OpenAI compatible grader requires base_url, api_key, and model")

        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._http_client_factory = http_client_factory or self._default_http_client_factory

    async def grade(self, essay_text: str, correction_input: EssayCorrectionInput) -> GradingResult:
        request_body = self._build_request_body(essay_text, correction_input)
        async with self._http_client_factory() as client:
            response_json = await self._post_with_retries(client, request_body)
        content = response_json["choices"][0]["message"]["content"]
        return self._parse_model_content(content)

    async def _post_with_retries(self, client: Any, request_body: dict[str, Any]) -> dict[str, Any]:
        last_error: httpx.HTTPStatusError | httpx.RequestError | None = None
        for _attempt in range(3):
            try:
                response = await client.post(
                    self._chat_completions_url,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=request_body,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code not in {502, 503, 504}:
                    break
            except httpx.RequestError as exc:
                last_error = exc

        raise EssayGraderError("Essay grading provider is temporarily unavailable") from last_error

    @property
    def _chat_completions_url(self) -> str:
        if self._base_url.endswith("/v1"):
            return f"{self._base_url}/chat/completions"
        return f"{self._base_url}/v1/chat/completions"

    def _build_request_body(
        self, essay_text: str, correction_input: EssayCorrectionInput
    ) -> dict[str, Any]:
        return {
            "model": self._model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": self._system_prompt(),
                },
                {
                    "role": "user",
                    "content": self._user_prompt(essay_text, correction_input),
                },
            ],
        }

    @staticmethod
    def _system_prompt() -> str:
        return (
            "你是一名有经验的小学语文老师。请根据作文题目、要求和学生作文文本进行批改。"
            "必须只输出一个 JSON 对象，不要输出 Markdown 或额外解释。"
            "分数范围：total 0-100；content、structure、language、mechanics、presentation 各 0-20。"
            "评语要具体、温和、适合小学生理解；teacherNotes 给老师或家长看，可以稍微专业一些。"
        )

    @staticmethod
    def _user_prompt(essay_text: str, correction_input: EssayCorrectionInput) -> str:
        return (
            "请批改下面这篇小学语文作文，并严格返回如下 JSON 结构：\n"
            "{\n"
            '  "score": {"total": 0, "content": 0, "structure": 0, "language": 0, "mechanics": 0, "presentation": 0},\n'
            '  "comments": {\n'
            '    "summary": "",\n'
            '    "strengths": [],\n'
            '    "issues": [],\n'
            '    "suggestions": [],\n'
            '    "encouragement": "",\n'
            '    "spellingIssues": [],\n'
            '    "sentenceIssues": [],\n'
            '    "revisionExample": "",\n'
            '    "teacherNotes": ""\n'
            "  }\n"
            "}\n\n"
            f"作文题目：{correction_input.title}\n"
            f"作文要求：{correction_input.requirements or '无'}\n"
            f"年级：{correction_input.grade_level}\n"
            f"作文类型：{correction_input.essay_type}\n\n"
            f"学生作文 OCR 文本：\n{essay_text}"
        )

    @staticmethod
    def _parse_model_content(content: str) -> GradingResult:
        payload = json.loads(OpenAICompatibleEssayGrader._extract_json_text(content))
        return GradingResult(
            score=EssayScore(**payload["score"]),
            comments=EssayComments(**payload["comments"]),
        )

    @staticmethod
    def _extract_json_text(content: str) -> str:
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            stripped = "\n".join(lines).strip()
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model response did not contain a JSON object")
        return stripped[start : end + 1]

    @staticmethod
    def _default_http_client_factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=90.0, trust_env=False)
