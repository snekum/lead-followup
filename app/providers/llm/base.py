"""LLM provider port.

A minimal interface over the Messages API agent loop: one `create` call returns
normalized content blocks (text + tool_use, as plain dicts mirroring the
Anthropic shape) and a stop reason. The real ``ClaudeClient`` and the offline
``FakeLLMClient`` both implement it, so the assistant is testable without keys.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    # Each block is {"type": "text", "text": ...} or
    # {"type": "tool_use", "id": ..., "name": ..., "input": {...}}.
    content: list[dict[str, object]]
    stop_reason: str


class LLMClient(ABC):
    @abstractmethod
    def create(
        self,
        *,
        system: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
        max_tokens: int = 512,
    ) -> LLMResponse: ...
