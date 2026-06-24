"""Select the configured LLM client."""
from __future__ import annotations

from app.config import get_settings
from app.providers.llm.base import LLMClient


def get_llm_client() -> LLMClient:
    provider = get_settings().llm_provider
    if provider == "fake":
        from app.providers.llm.fake import FakeLLMClient

        return FakeLLMClient()
    if provider == "claude":
        from app.providers.llm.claude import ClaudeClient

        return ClaudeClient()
    # default: Gemini
    from app.providers.llm.gemini import GeminiClient

    return GeminiClient()
