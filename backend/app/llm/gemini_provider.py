from __future__ import annotations

import asyncio
import json

import httpx

from app.llm.base import STRICT_FLAT_FAULT_TREE_SCHEMA, LLMGenerationError, LLMProvider

TOOL_NAME = "emit_fault_tree"
API_BASE = "https://generativelanguage.googleapis.com/v1beta"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3


class GeminiProvider(LLMProvider):
    provider_name = "gemini"
    default_model = "gemini-3.8-flash"

    async def complete_structured(
        self,
        *,
        system_prompt: str,
        messages: list[dict],
        api_key: str,
        model: str | None,
    ) -> str:
        contents = [
            {
                "role": "model" if message["role"] == "assistant" else "user",
                "parts": [{"text": message["content"]}],
            }
            for message in messages
        ]
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "tools": [
                {
                    "functionDeclarations": [
                        {
                            "name": TOOL_NAME,
                            "description": "Emit the fault tree as a flat list of nodes.",
                            "parametersJsonSchema": STRICT_FLAT_FAULT_TREE_SCHEMA,
                        }
                    ]
                }
            ],
            "toolConfig": {
                "functionCallingConfig": {
                    "mode": "ANY",
                    "allowedFunctionNames": [TOOL_NAME],
                }
            },
        }
        url = f"{API_BASE}/models/{model or self.default_model}:generateContent"

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                for attempt in range(MAX_ATTEMPTS):
                    response = await client.post(url, params={"key": api_key}, json=payload)
                    if response.status_code not in RETRYABLE_STATUS_CODES or attempt == MAX_ATTEMPTS - 1:
                        break
                    await asyncio.sleep(2**attempt)
        except httpx.HTTPError as e:
            raise LLMGenerationError(f"Could not reach Google Gemini: {e}") from e

        if response.status_code in (401, 403):
            raise LLMGenerationError("Invalid Google Gemini API key")
        if response.is_error:
            try:
                detail = response.json()["error"]["message"]
            except (ValueError, KeyError, TypeError):
                detail = response.text
            raise LLMGenerationError(f"Google Gemini API error: {detail}")

        try:
            parts = response.json()["candidates"][0]["content"]["parts"]
            function_call = next(part["functionCall"] for part in parts if "functionCall" in part)
            return json.dumps(function_call["args"])
        except (ValueError, KeyError, IndexError, StopIteration) as e:
            raise LLMGenerationError("Gemini response did not include a function call") from e
