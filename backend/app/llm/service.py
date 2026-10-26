"""Orchestrates the LLM drafting call: generate -> validate -> retry loop.

This is the "LLM drafts, code verifies" split the product relies on: the provider's
`strict` mode reduces malformed *syntax*, Pydantic + graph validation catch malformed
*semantics* (dangling refs, cycles, shared gates, gate/basic field misuse), and on any
failure the concrete validation error is fed back to the model for self-correction --
capped at MAX_ATTEMPTS, after which a clean LLMGenerationError propagates to the API
layer as a 422.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from app.domain.models import FaultTree, LLMFaultTreeResponse
from app.domain.tree_builder import build_fault_tree
from app.domain.tree_validation import TreeValidationError
from app.llm.base import LLMGenerationError, LLMProvider
from app.llm.prompts import SYSTEM_PROMPT, build_retry_prompt, build_user_prompt

async def generate_fault_tree(
    provider: LLMProvider,
    api_key: str,
    model: str | None,
    threat_model_markdown: str,
    top_event_text: str,
    max_attempts: int = 3,
) -> tuple[FaultTree, list[str]]:
    messages: list[dict] = [
        {"role": "user", "content": build_user_prompt(threat_model_markdown, top_event_text)}
    ]

    last_error: Exception | None = None
    for _attempt in range(max_attempts):
        raw = await provider.complete_structured(
            system_prompt=SYSTEM_PROMPT, messages=messages, api_key=api_key, model=model
        )
        try:
            parsed = LLMFaultTreeResponse.model_validate_json(raw)
            tree, warnings = build_fault_tree(parsed, top_event_text)
            return tree, warnings
        except (ValidationError, TreeValidationError, json.JSONDecodeError) as e:
            last_error = e
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": build_retry_prompt(str(e))})

    raise LLMGenerationError(
        f"Could not obtain a valid fault tree after {max_attempts} attempts: {last_error}"
    )
