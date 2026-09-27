"""DeepSeek Chat Completions adapter and the exact request record."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal, Protocol, TypedDict, assert_never

from openai import APIStatusError, OpenAI, OpenAIError
from openai.types.chat import ChatCompletionMessageParam


class Message(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class ChatRequest:
    model: str
    messages: list[Message]
    max_tokens: int = 180
    temperature: float = 0.3
    thinking: Literal["disabled"] = "disabled"

    def as_record(self) -> dict[str, str | int | float | list[Message]]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ModelResult:
    answer: str
    raw_response_json: str
    response_model: str


@dataclass(frozen=True, slots=True)
class ProviderError(Exception):
    code: str
    detail: str
    raw_response: str | None = None

    def __str__(self) -> str:
        return self.detail


class ModelProvider(Protocol):
    def complete(self, request: ChatRequest) -> ModelResult: ...


class DeepSeekProvider:
    def __init__(
        self, api_key: str, base_url: str = "https://api.deepseek.com"
    ) -> None:
        self._client = OpenAI(
            api_key=api_key, base_url=base_url, timeout=45.0, max_retries=0
        )

    def complete(self, request: ChatRequest) -> ModelResult:
        messages: list[ChatCompletionMessageParam] = []
        for message in request.messages:
            match message["role"]:
                case "system":
                    messages.append({"role": "system", "content": message["content"]})
                case "user":
                    messages.append({"role": "user", "content": message["content"]})
                case "assistant":
                    messages.append(
                        {"role": "assistant", "content": message["content"]}
                    )
                case unreachable:
                    assert_never(unreachable)
        try:
            response = self._client.chat.completions.create(
                model=request.model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=False,
                extra_body={"thinking": {"type": request.thinking}},
            )
        except OpenAIError as exc:
            raw_response = (
                exc.response.text if isinstance(exc, APIStatusError) else None
            )
            raise ProviderError(
                type(exc).__name__, str(exc)[:1000], raw_response
            ) from exc
        if (
            not response.choices
            or not (response.choices[0].message.content or "").strip()
        ):
            raise ProviderError(
                "empty_response",
                "The model returned no answer.",
                response.model_dump_json(),
            )
        answer = response.choices[0].message.content
        assert answer is not None
        return ModelResult(answer.strip(), response.model_dump_json(), response.model)
