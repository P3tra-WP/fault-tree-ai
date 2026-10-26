from app.domain.models import (
    AnalysisResult,
    BasicEvent,
    CutSet,
    FaultTree,
    Gate,
    ProbabilityResult,
    TopEvent,
)
from sqlalchemy import select

from app.storage.database_store import AnalysisCutSetRecord, DatabaseStore


def _result() -> AnalysisResult:
    return AnalysisResult(
        analysis_id="analysis-1",
        top_event=TopEvent(description="Top event"),
        fault_tree=FaultTree(
            top_event=TopEvent(description="Top event"),
            root=Gate(
                id="root",
                gate_type="OR",
                description="Top event",
                children=[BasicEvent(id="event-1", description="Basic event", probability=0.1)],
            ),
        ),
        minimal_cut_sets=[
            CutSet(
                event_ids=["event-1"],
                event_descriptions=["Basic event"],
                baseline_probability=0.1,
                residual_probability=0.1,
            )
        ],
        baseline_probability=ProbabilityResult(top_event_probability=0.1, method="exact"),
        residual_probability=ProbabilityResult(top_event_probability=0.1, method="exact"),
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


def test_store_persists_analysis_and_materialized_cut_sets(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'fault-tree-ai.db'}"
    store = DatabaseStore(database_url)
    store.save(_result())

    restarted_store = DatabaseStore(database_url)
    restored = restarted_store.get("analysis-1")

    assert restored is not None
    assert restored.fault_tree.root.children[0].description == "Basic event"
    assert restored.minimal_cut_sets[0].event_ids == ["event-1"]

    with restarted_store._session_factory()() as session:
        rows = session.scalars(select(AnalysisCutSetRecord)).all()

    assert len(rows) == 1
    assert rows[0].event_descriptions == ["Basic event"]
