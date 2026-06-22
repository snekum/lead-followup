"""Anthropic Claude implementation of the LLM port."""
from __future__ import annotations

from app.config import get_settings
from app.providers.llm.base import LLMClient, LLMResponse


class ClaudeClient(LLMClient):
    def __init__(self) -> None:
        import anthropic

        settings = get_settings()
        # api_key=None lets the SDK read ANTHROPIC_API_KEY from the environment.
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None)
        self._model = settings.anthropic_model

    def create(
        self,
        *,
        system: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
        max_tokens: int = 512,
    ) -> LLMResponse:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,  # type: ignore[arg-type]
            tools=tools,  # type: ignore[arg-type]
        )
        content: list[dict[str, object]] = []
        for block in response.content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                content.append({"type": "text", "text": getattr(block, "text", "")})
            elif block_type == "tool_use":
                content.append(
                    {
                        "type": "tool_use",
                        "id": getattr(block, "id", ""),
                        "name": getattr(block, "name", ""),
                        "input": getattr(block, "input", {}),
                    }
                )
        return LLMResponse(content=content, stop_reason=response.stop_reason or "end_turn")
