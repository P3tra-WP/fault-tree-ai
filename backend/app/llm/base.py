"""Provider-agnostic interface for the single thing the LLM is asked to do: draft a
flat fault-tree node list from a threat model + top event, as a forced tool call
against FLAT_FAULT_TREE_SCHEMA. Both providers return the raw JSON text; parsing and
validation happen one level up in llm/service.py, not here.
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod

from app.domain.models import FLAT_FAULT_TREE_SCHEMA  # noqa: F401  (re-exported for providers)


def to_strict_schema(schema: dict) -> dict:
    """Adapts a Pydantic-generated JSON schema for provider "strict" structured-output
    modes, which require every object property to be listed in `required` (an optional
    field is represented as a nullable type rather than being omitted -- which Pydantic
    already does for Optional[...] fields, so this only needs to fix up `required` and
    `additionalProperties`).
    """
    schema = copy.deepcopy(schema)

    def process(node: dict) -> None:
        if not isinstance(node, dict):
            return
        if node.get("type") == "object" and "properties" in node:
            node["additionalProperties"] = False
            node["required"] = list(node["properties"].keys())
            for prop_schema in node["properties"].values():
                process(prop_schema)
        if node.get("type") == "array" and "items" in node:
            process(node["items"])
        for key in ("anyOf", "oneOf", "allOf"):
            if key in node:
                for sub in node[key]:
                    process(sub)
        if "$defs" in node:
            for def_schema in node["$defs"].values():
                process(def_schema)

    process(schema)
    return schema


STRICT_FLAT_FAULT_TREE_SCHEMA = to_strict_schema(FLAT_FAULT_TREE_SCHEMA)


class LLMGenerationError(Exception):
    """Raised when a provider call fails (auth, transport, rate limit, etc)."""


class LLMProvider(ABC):
    provider_name: str
    default_model: str

    @abstractmethod
    async def complete_structured(
        self,
        *,
        system_prompt: str,
        messages: list[dict],
        api_key: str,
        model: str | None,
    ) -> str:
        """Returns raw JSON text matching FLAT_FAULT_TREE_SCHEMA.

        Raises LLMGenerationError on transport/auth failure. Does not validate the
        JSON's shape -- that is the caller's responsibility (llm/service.py).
        """
        raise NotImplementedError
