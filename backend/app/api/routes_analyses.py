"""Every mutation here (generation, edit, import) re-runs the full
cutsets/probability/risk pipeline server-side -- pure math, no LLM involved except in
the initial generation call -- and returns the complete AnalysisResult, so the
frontend never computes domain logic itself, only renders.

Analyses and their computed cut sets are stored in SQL. No auth: this is a local,
single-user, BYOK tool.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.config import settings
from app.domain.controls import build_probability_lookups
from app.domain.cutsets import compute_minimal_cutsets
from app.domain.merge import import_fault_tree
from app.domain.models import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisUpdateRequest,
    Control,
    FaultTree,
    ImportRequest,
    LossMagnitude,
)
from app.domain.probability import build_cut_set_models, compute_probability
from app.domain.risk import compute_risk_quantification
from app.domain.tree_validation import TreeValidationError, validate_fault_tree
from app.export.markdown_report import render_markdown_report
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import LLMGenerationError, LLMProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.service import generate_fault_tree
from app.storage.database_store import store

router = APIRouter()

PROVIDERS: dict[str, LLMProvider] = {
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "gemini": GeminiProvider(),
}


class CreateFromImportRequest(BaseModel):
    fault_tree: FaultTree


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assemble_result(
    *,
    analysis_id: str,
    fault_tree: FaultTree,
    controls: list[Control],
    loss_magnitude: LossMagnitude | None,
    provider: str | None,
    model: str | None,
    created_at: str,
    extra_warnings: list[str],
) -> AnalysisResult:
    structural_warnings = validate_fault_tree(fault_tree)
    cutsets, cutset_warnings = compute_minimal_cutsets(fault_tree.root)
    baseline_lookup, residual_lookup, control_warnings = build_probability_lookups(
        fault_tree.root, controls
    )
    baseline_prob = compute_probability(fault_tree.root, cutsets, baseline_lookup)
    residual_prob = compute_probability(fault_tree.root, cutsets, residual_lookup)
    cut_set_models = build_cut_set_models(cutsets, fault_tree.root, baseline_lookup, residual_lookup)

    risk = None
    if loss_magnitude is not None:
        risk = compute_risk_quantification(loss_magnitude, baseline_prob, residual_prob)

    return AnalysisResult(
        analysis_id=analysis_id,
        top_event=fault_tree.top_event,
        fault_tree=fault_tree,
        controls=controls,
        minimal_cut_sets=cut_set_models,
        baseline_probability=baseline_prob,
        residual_probability=residual_prob,
        risk_quantification=risk,
        provider=provider,
        model=model,
        created_at=created_at,
        updated_at=_now(),
        warnings=[*extra_warnings, *structural_warnings, *cutset_warnings, *control_warnings],
    )


@router.post("/analyses", response_model=AnalysisResult)
async def create_analysis(request: AnalysisRequest) -> AnalysisResult:
    if len(request.threat_model_markdown.encode("utf-8")) > settings.max_threat_model_bytes:
        raise HTTPException(status_code=413, detail="Threat model markdown exceeds size limit")

    provider = PROVIDERS[request.provider]
    try:
        fault_tree, warnings = await generate_fault_tree(
            provider=provider,
            api_key=request.api_key,
            model=request.model,
            threat_model_markdown=request.threat_model_markdown,
            top_event_text=request.top_event,
            max_attempts=settings.max_llm_attempts,
        )
    except LLMGenerationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    analysis_id = store.new_id()
    result = _assemble_result(
        analysis_id=analysis_id,
        fault_tree=fault_tree,
        controls=[],
        loss_magnitude=None,
        provider=request.provider,
        model=request.model or provider.default_model,
        created_at=_now(),
        extra_warnings=warnings,
    )
    store.save(result)
    return result


@router.post("/analyses/import", response_model=AnalysisResult)
def create_analysis_from_import(request: CreateFromImportRequest) -> AnalysisResult:
    try:
        validate_fault_tree(request.fault_tree)
    except TreeValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    analysis_id = store.new_id()
    result = _assemble_result(
        analysis_id=analysis_id,
        fault_tree=request.fault_tree,
        controls=[],
        loss_magnitude=None,
        provider=None,
        model=None,
        created_at=_now(),
        extra_warnings=[],
    )
    store.save(result)
    return result


@router.get("/analyses/{analysis_id}", response_model=AnalysisResult)
def get_analysis(analysis_id: str) -> AnalysisResult:
    result = store.get(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return result


@router.put("/analyses/{analysis_id}", response_model=AnalysisResult)
def update_analysis(analysis_id: str, request: AnalysisUpdateRequest) -> AnalysisResult:
    existing = store.get(analysis_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    try:
        validate_fault_tree(request.fault_tree)
    except TreeValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    result = _assemble_result(
        analysis_id=analysis_id,
        fault_tree=request.fault_tree,
        controls=request.controls,
        loss_magnitude=request.loss_magnitude,
        provider=existing.provider,
        model=existing.model,
        created_at=existing.created_at,
        extra_warnings=[],
    )
    store.save(result)
    return result


@router.post("/analyses/{analysis_id}/import", response_model=AnalysisResult)
def import_into_analysis(analysis_id: str, request: ImportRequest) -> AnalysisResult:
    existing = store.get(analysis_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    import_sequence = store.next_import_sequence(analysis_id)
    try:
        merged_tree, merge_warnings = import_fault_tree(
            current_tree=existing.fault_tree,
            imported_tree=request.fault_tree,
            mode=request.mode,
            attach_gate_id=request.attach_gate_id,
            import_sequence=import_sequence,
        )
        validate_fault_tree(merged_tree)
    except TreeValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Replacing the tree invalidates existing controls/loss magnitude (they referenced
    # the old tree's basic-event ids); merging keeps them since the old ids still exist.
    controls = existing.controls if request.mode == "merge" else []
    loss_magnitude = (
        existing.risk_quantification.loss_magnitude
        if request.mode == "merge" and existing.risk_quantification
        else None
    )

    result = _assemble_result(
        analysis_id=analysis_id,
        fault_tree=merged_tree,
        controls=controls,
        loss_magnitude=loss_magnitude,
        provider=existing.provider,
        model=existing.model,
        created_at=existing.created_at,
        extra_warnings=merge_warnings,
    )
    store.save(result)
    return result


@router.get("/analyses/{analysis_id}/export")
def export_analysis(analysis_id: str, format: str = "json") -> Response:
    result = store.get(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if format == "markdown":
        content = render_markdown_report(result)
        media_type = "text/markdown"
        filename = f"{analysis_id}.md"
    elif format == "json":
        content = result.model_dump_json(indent=2)
        media_type = "application/json"
        filename = f"{analysis_id}.json"
    else:
        raise HTTPException(status_code=400, detail="format must be 'json' or 'markdown'")

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
