from __future__ import annotations

import openai

from app.llm.base import STRICT_FLAT_FAULT_TREE_SCHEMA, LLMGenerationError, LLMProvider

TOOL_NAME = "emit_fault_tree"


class OpenAIProvider(LLMProvider):
    provider_name = "openai"
    # NOTE: verify this id against the current OpenAI model catalog at implementation
    # time -- the forced-function-call pattern below is stable, the model id is not.
    default_model = "gpt-5"

    async def complete_structured(
        self,
        *,
        system_prompt: str,
        messages: list[dict],
        api_key: str,
        model: str | None,
    ) -> str:
        client = openai.AsyncOpenAI(api_key=api_key)
        try:
            response = await client.chat.completions.create(
                model=model or self.default_model,
                messages=[{"role": "system", "content": system_prompt}, *messages],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": TOOL_NAME,
                            "description": "Emit the fault tree as a flat list of nodes.",
                            "parameters": STRICT_FLAT_FAULT_TREE_SCHEMA,
                            "strict": True,
                        },
                    }
                ],
                tool_choice={"type": "function", "function": {"name": TOOL_NAME}},
            )
        except openai.AuthenticationError as e:
            raise LLMGenerationError("Invalid OpenAI API key") from e
        except openai.APIStatusError as e:
            raise LLMGenerationError(f"OpenAI API error: {e.message}") from e
        except openai.APIConnectionError as e:
            raise LLMGenerationError(f"Could not reach OpenAI: {e}") from e

        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            raise LLMGenerationError("OpenAI response did not include a tool call")
        return tool_calls[0].function.arguments
