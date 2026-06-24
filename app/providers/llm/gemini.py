"""Google Gemini implementation of the LLM port (google-genai SDK).

Translates the port's Anthropic-shaped messages (text / tool_use / tool_result
blocks) to/from Gemini's Content/Part model. Gemini correlates tool results by
function *name* rather than an id, so we recover the name from the preceding
tool_use blocks.
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.providers.llm.base import LLMClient, LLMResponse


def _tool_names(messages: list[dict[str, object]]) -> dict[str, str]:
    """Map each tool_use id to its function name (from assistant tool_use blocks)."""
    names: dict[str, str] = {}
    for message in messages:
        content = message.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    names[str(block.get("id"))] = str(block.get("name"))
    return names


class GeminiClient(LLMClient):
    def __init__(self) -> None:
        from google import genai

        settings = get_settings()
        # api_key=None lets the SDK read GOOGLE_API_KEY from the environment.
        self._client = genai.Client(api_key=settings.google_api_key or None)
        self._model = settings.gemini_model

    def create(
        self,
        *,
        system: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
        max_tokens: int = 512,
    ) -> LLMResponse:
        from google.genai import types

        contents = self._build_contents(messages, _tool_names(messages), types)
        config = types.GenerateContentConfig(
            system_instruction=system or None,
            max_output_tokens=max_tokens,
            tools=[self._build_tool(tools, types)] if tools else None,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        response = self._client.models.generate_content(
            model=self._model, contents=contents, config=config
        )
        return self._parse(response)

    @staticmethod
    def _build_tool(tools: list[dict[str, object]], types: Any) -> Any:
        declarations = [
            types.FunctionDeclaration(
                name=str(tool["name"]),
                description=str(tool.get("description", "")),
                parameters_json_schema=tool.get("input_schema")
                or {"type": "object", "properties": {}},
            )
            for tool in tools
        ]
        return types.Tool(function_declarations=declarations)

    @staticmethod
    def _build_contents(
        messages: list[dict[str, object]], id_to_name: dict[str, str], types: Any
    ) -> list[Any]:
        contents: list[Any] = []
        for message in messages:
            role = message.get("role")
            content = message.get("content")

            if isinstance(content, str):
                gem_role = "user" if role == "user" else "model"
                contents.append(
                    types.Content(role=gem_role, parts=[types.Part.from_text(text=content)])
                )
                continue

            if not isinstance(content, list):
                continue

            if role == "assistant":
                parts = []
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text" and block.get("text"):
                        parts.append(types.Part.from_text(text=str(block["text"])))
                    elif block.get("type") == "tool_use":
                        parts.append(
                            types.Part(
                                function_call=types.FunctionCall(
                                    name=str(block.get("name")),
                                    args=block.get("input") or {},
                                )
                            )
                        )
                if parts:
                    contents.append(types.Content(role="model", parts=parts))
            else:  # user turn carrying tool_result blocks
                parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        name = id_to_name.get(str(block.get("tool_use_id")), "tool")
                        parts.append(
                            types.Part.from_function_response(
                                name=name,
                                response={"result": str(block.get("content", ""))},
                            )
                        )
                if parts:
                    contents.append(types.Content(role="tool", parts=parts))
        return contents

    @staticmethod
    def _parse(response: Any) -> LLMResponse:
        candidates = getattr(response, "candidates", None)
        if not candidates:
            raise RuntimeError("Gemini returned no candidates (possibly safety-blocked)")
        parts = getattr(candidates[0].content, "parts", None) or []

        content: list[dict[str, object]] = []
        has_tool = False
        for index, part in enumerate(parts):
            function_call = getattr(part, "function_call", None)
            text = getattr(part, "text", None)
            if function_call is not None:
                has_tool = True
                content.append(
                    {
                        "type": "tool_use",
                        "id": f"gem-{index}-{getattr(function_call, 'name', '')}",
                        "name": getattr(function_call, "name", ""),
                        "input": dict(getattr(function_call, "args", {}) or {}),
                    }
                )
            elif text:
                content.append({"type": "text", "text": text})
        return LLMResponse(
            content=content, stop_reason="tool_use" if has_tool else "end_turn"
        )
