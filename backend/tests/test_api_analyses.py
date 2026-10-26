"""API round-trip tests. The LLMProvider boundary is stubbed -- no real network calls
are made to OpenAI/Anthropic here or anywhere else in this test suite.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.api import routes_analyses
from app.main import app

client = TestClient(app)

VALID_FLAT_TREE = {
    "top_event_id": "top",
    "nodes": [
        {
            "id": "top",
            "type": "GATE",
            "gate_type": "OR",
            "description": "Disaster",
            "children_ids": ["a", "b"],
        },
        {"id": "a", "type": "BASIC", "description": "Event A", "probability": 0.1},
        {"id": "b", "type": "BASIC", "description": "Event B", "probability": 0.2},
    ],
}


class StubProvider:
    """Replaces the real network call with a scripted sequence of responses."""

    provider_name = "openai"
    default_model = "stub-model"

    def __init__(self, responses):
        self._responses = list(responses)
        self.call_count = 0

    async def complete_structured(self, *, system_prompt, messages, api_key, model):
        self.call_count += 1
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return json.dumps(response)


@pytest.fixture(autouse=True)
def restore_providers():
    original = dict(routes_analyses.PROVIDERS)
    yield
    routes_analyses.PROVIDERS.clear()
    routes_analyses.PROVIDERS.update(original)


def _create(top_event="Top event", markdown="notes"):
    return client.post(
        "/api/analyses",
        json={
            "provider": "openai",
            "api_key": "sk-fake",
            "top_event": top_event,
            "threat_model_markdown": markdown,
        },
    )


def test_generate_success():
    routes_analyses.PROVIDERS["openai"] = StubProvider([VALID_FLAT_TREE])
    resp = _create()
    assert resp.status_code == 200
    body = resp.json()
    assert body["fault_tree"]["root"]["id"] == "top"
    assert body["baseline_probability"]["method"] == "exact"
    assert body["baseline_probability"]["top_event_probability"] is not None


def test_generate_accepts_gemini_provider():
    routes_analyses.PROVIDERS["gemini"] = StubProvider([VALID_FLAT_TREE])
    resp = client.post(
        "/api/analyses",
        json={
            "provider": "gemini",
            "api_key": "AIza-fake",
            "top_event": "Top event",
            "threat_model_markdown": "notes",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["provider"] == "gemini"


def test_generate_retries_then_succeeds():
    stub = StubProvider(["not json", VALID_FLAT_TREE])
    routes_analyses.PROVIDERS["openai"] = stub
    resp = _create()
    assert resp.status_code == 200
    assert stub.call_count == 2


def test_generate_exhausts_retries_returns_422():
    stub = StubProvider(["not json", "still not json", "still not json"])
    routes_analyses.PROVIDERS["openai"] = stub
    resp = _create()
    assert resp.status_code == 422


def test_generate_uses_configured_retry_limit(monkeypatch):
    stub = StubProvider(["not json", "still not json"])
    routes_analyses.PROVIDERS["openai"] = stub
    monkeypatch.setattr(routes_analyses.settings, "max_llm_attempts", 2)

    resp = _create()

    assert resp.status_code == 422
    assert stub.call_count == 2
    assert "after 2 attempts" in resp.json()["detail"]


def test_get_analysis_round_trip():
    routes_analyses.PROVIDERS["openai"] = StubProvider([VALID_FLAT_TREE])
    created = _create().json()
    resp = client.get(f"/api/analyses/{created['analysis_id']}")
    assert resp.status_code == 200
    assert resp.json()["analysis_id"] == created["analysis_id"]


def test_get_unknown_analysis_returns_404():
    resp = client.get("/api/analyses/does-not-exist")
    assert resp.status_code == 404


def test_put_recomputes_after_edit_with_control_and_loss_magnitude():
    routes_analyses.PROVIDERS["openai"] = StubProvider([VALID_FLAT_TREE])
    created = _create().json()

    fault_tree = created["fault_tree"]
    fault_tree["root"]["children"][0]["probability"] = 0.8  # bump event `a`
    target_id = fault_tree["root"]["children"][0]["id"]

    resp = client.put(
        f"/api/analyses/{created['analysis_id']}",
        json={
            "fault_tree": fault_tree,
            "controls": [
                {
                    "id": "c1",
                    "description": "MFA",
                    "target_basic_event_id": target_id,
                    "effectiveness": 0.5,
                    "active": True,
                }
            ],
            "loss_magnitude": {"amount": 1000000, "currency": "USD", "time_base": "annual"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert (
        body["baseline_probability"]["top_event_probability"]
        != body["residual_probability"]["top_event_probability"]
    )
    assert body["risk_quantification"]["baseline_ale"] is not None
    assert body["risk_quantification"]["savings"] > 0


def test_import_merge_round_trip():
    routes_analyses.PROVIDERS["openai"] = StubProvider([VALID_FLAT_TREE])
    created = _create().json()

    resp = client.post(
        f"/api/analyses/{created['analysis_id']}/import",
        json={"fault_tree": created["fault_tree"], "mode": "merge", "attach_gate_id": "top"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # Original 2 children (a, b) plus one imported subtree root = 3.
    assert len(body["fault_tree"]["root"]["children"]) == 3


def test_export_json_and_markdown():
    routes_analyses.PROVIDERS["openai"] = StubProvider([VALID_FLAT_TREE])
    created = _create().json()

    json_resp = client.get(f"/api/analyses/{created['analysis_id']}/export?format=json")
    assert json_resp.status_code == 200
    assert json_resp.headers["content-type"].startswith("application/json")

    md_resp = client.get(f"/api/analyses/{created['analysis_id']}/export?format=markdown")
    assert md_resp.status_code == 200
    assert "Fault Tree Analysis" in md_resp.text
