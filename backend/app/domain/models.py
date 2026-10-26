"""Core domain models for fault trees, controls, and risk quantification.

Two schema "layers" live in this module:

- The LLM-facing *flat* schema (`LLMNode`, `LLMFaultTreeResponse`): a non-recursive
  representation used only for the initial LLM generation call, since neither OpenAI's
  nor Anthropic's strict structured-output schemas support recursive JSON Schema.
- The internal *nested* domain model (`Gate`, `BasicEvent`, `FaultTree`, ...): used
  everywhere else — API responses, the deterministic math, the editor.

`tree_builder.py` converts flat -> nested (LLM path). `tree_validation.py` validates an
already-nested tree (edit/import path).
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator

# --------------------------------------------------------------------------
# LLM-facing flat schema
# --------------------------------------------------------------------------


class LLMNode(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    type: Literal["GATE", "BASIC"]
    gate_type: Optional[Literal["AND", "OR"]] = None
    description: str
    children_ids: list[str] = Field(default_factory=list)
    probability: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    rationale: Optional[str] = None

    @model_validator(mode="after")
    def check_consistency(self) -> "LLMNode":
        if self.type == "GATE":
            if self.gate_type is None:
                raise ValueError(f"Gate node {self.id} is missing gate_type")
            if not self.children_ids:
                raise ValueError(f"Gate node {self.id} has no children")
            if self.probability is not None:
                raise ValueError(f"Gate node {self.id} must not have a probability")
        else:  # BASIC
            if self.children_ids:
                raise ValueError(f"Basic event {self.id} must not have children")
            if self.gate_type is not None:
                raise ValueError(f"Basic event {self.id} must not have a gate_type")
        return self


class LLMFaultTreeResponse(BaseModel):
    model_config = {"extra": "forbid"}

    top_event_id: str
    nodes: list[LLMNode]

    @model_validator(mode="after")
    def check_graph_shape(self) -> "LLMFaultTreeResponse":
        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate node ids in LLM response")
        id_set = set(ids)
        if self.top_event_id not in id_set:
            raise ValueError("top_event_id not found among nodes")
        for n in self.nodes:
            for c in n.children_ids:
                if c not in id_set:
                    raise ValueError(f"Node {n.id} references unknown child {c}")
        return self


# The JSON schema handed to both providers as a forced tool/function call.
FLAT_FAULT_TREE_SCHEMA = LLMFaultTreeResponse.model_json_schema()


# --------------------------------------------------------------------------
# Internal nested domain model
# --------------------------------------------------------------------------


class TopEvent(BaseModel):
    description: str


class BasicEvent(BaseModel):
    node_type: Literal["BASIC"] = "BASIC"
    id: str
    description: str
    probability: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    rationale: Optional[str] = None


class Gate(BaseModel):
    node_type: Literal["GATE"] = "GATE"
    id: str
    gate_type: Literal["AND", "OR"]
    description: str
    children: list["FaultTreeNode"]


FaultTreeNode = Annotated[Union[Gate, BasicEvent], Field(discriminator="node_type")]
Gate.model_rebuild()


class FaultTree(BaseModel):
    top_event: TopEvent
    root: Gate


# --------------------------------------------------------------------------
# Controls & risk quantification
# --------------------------------------------------------------------------


class Control(BaseModel):
    id: str
    description: str
    target_basic_event_id: str
    effectiveness: float = Field(ge=0.0, le=1.0)
    active: bool = True
    rationale: Optional[str] = None


class LossMagnitude(BaseModel):
    amount: float = Field(gt=0)
    currency: str = "USD"
    time_base: str = "annual"  # a label only -- no unit conversion is performed


class RiskQuantification(BaseModel):
    loss_magnitude: LossMagnitude
    baseline_ale: Optional[float] = None
    residual_ale: Optional[float] = None
    savings: Optional[float] = None


# --------------------------------------------------------------------------
# Analysis results
# --------------------------------------------------------------------------


class ProbabilityResult(BaseModel):
    top_event_probability: Optional[float] = None
    method: Literal["exact", "approximate_rare_event", "unavailable"]
    warnings: list[str] = Field(default_factory=list)


class CutSet(BaseModel):
    event_ids: list[str]
    event_descriptions: list[str]
    baseline_probability: Optional[float] = None
    residual_probability: Optional[float] = None


class AnalysisResult(BaseModel):
    analysis_id: str
    top_event: TopEvent
    fault_tree: FaultTree
    controls: list[Control] = Field(default_factory=list)
    minimal_cut_sets: list[CutSet] = Field(default_factory=list)
    baseline_probability: ProbabilityResult
    residual_probability: ProbabilityResult
    risk_quantification: Optional[RiskQuantification] = None
    provider: Optional[Literal["openai", "anthropic", "gemini"]] = None
    model: Optional[str] = None
    created_at: str
    updated_at: str
    warnings: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# API request bodies
# --------------------------------------------------------------------------


class AnalysisRequest(BaseModel):
    provider: Literal["openai", "anthropic", "gemini"]
    api_key: str
    model: Optional[str] = None
    top_event: str = Field(..., min_length=1, max_length=2000)
    threat_model_markdown: str = Field(..., min_length=1, max_length=200_000)


class AnalysisUpdateRequest(BaseModel):
    fault_tree: FaultTree
    controls: list[Control] = Field(default_factory=list)
    loss_magnitude: Optional[LossMagnitude] = None


class ImportRequest(BaseModel):
    fault_tree: FaultTree
    mode: Literal["replace", "merge"]
    attach_gate_id: Optional[str] = None
