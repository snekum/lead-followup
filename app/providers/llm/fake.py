"""Scriptable in-memory LLM, for tests and offline demos."""
from __future__ import annotations

from app.providers.llm.base import LLMClient, LLMResponse


def text_response(text: str) -> LLMResponse:
    return LLMResponse(content=[{"type": "text", "text": text}], stop_reason="end_turn")


def tool_response(tool_id: str, name: str, tool_input: dict[str, object]) -> LLMResponse:
    return LLMResponse(
        content=[{"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}],
        stop_reason="tool_use",
    )


class FakeLLMClient(LLMClient):
    """Returns scripted responses in order, then falls back to a default."""

    def __init__(
        self,
        responses: list[LLMResponse] | None = None,
        default: LLMResponse | None = None,
    ) -> None:
        self._responses = list(responses or [])
        self._default = default or text_response(
            "Thanks for your message! How can I help you with your Tata car?"
        )

    def create(
        self,
        *,
        system: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
        max_tokens: int = 512,
    ) -> LLMResponse:
        if self._responses:
            return self._responses.pop(0)
        return self._default
