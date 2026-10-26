from __future__ import annotations

import json

import anthropic

from app.llm.base import STRICT_FLAT_FAULT_TREE_SCHEMA, LLMGenerationError, LLMProvider

TOOL_NAME = "emit_fault_tree"


class AnthropicProvider(LLMProvider):
    provider_name = "anthropic"
    default_model = "claude-sonnet-5"

    async def complete_structured(
        self,
        *,
        system_prompt: str,
        messages: list[dict],
        api_key: str,
        model: str | None,
    ) -> str:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        try:
            response = await client.messages.create(
                model=model or self.default_model,
                max_tokens=8000,
                system=system_prompt,
                messages=messages,
                tools=[
                    {
                        "name": TOOL_NAME,
                        "description": "Emit the fault tree as a flat list of nodes.",
                        "input_schema": STRICT_FLAT_FAULT_TREE_SCHEMA,
                        "strict": True,
                    }
                ],
                tool_choice={"type": "tool", "name": TOOL_NAME},
            )
        except anthropic.AuthenticationError as e:
            raise LLMGenerationError("Invalid Anthropic API key") from e
        except anthropic.APIStatusError as e:
            raise LLMGenerationError(f"Anthropic API error: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise LLMGenerationError(f"Could not reach Anthropic: {e}") from e

        tool_use = next((b for b in response.content if b.type == "tool_use"), None)
        if tool_use is None:
            raise LLMGenerationError("Anthropic response did not include a tool_use block")
        return json.dumps(tool_use.input)
