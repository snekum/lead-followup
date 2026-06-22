"""Select the configured LLM client."""
from __future__ import annotations

from app.config import get_settings
from app.providers.llm.base import LLMClient


def get_llm_client() -> LLMClient:
    if get_settings().llm_provider == "fake":
        from app.providers.llm.fake import FakeLLMClient

        return FakeLLMClient()
    from app.providers.llm.claude import ClaudeClient

    return ClaudeClient()
