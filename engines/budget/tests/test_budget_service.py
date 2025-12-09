from __future__ import annotations

from engines.budget.service import BudgetIngestor, BudgetService


class DummyVertexClient:
    def list_usage(self, timeframe):
        return [{"model": "gemini", "tokens": 1000, "calls": 2, "cost": 1.2, "project": "p1"}]


class DummyBedrockClient:
    def list_usage(self, timeframe):
        return [{"model": "anthropic.claude", "tokens": 2000, "calls": 1, "cost": 2.5, "region": "us-east-1"}]


def test_ingest_vertex_usage_normalizes():
    ingestor = BudgetIngestor(vertex_client=DummyVertexClient())
    metrics = ingestor.ingest_vertex_usage(tenant_id="t_demo", timeframe="daily")
    assert metrics[0].vendor == "vertex"
    assert metrics[0].tokens == 1000


def test_ingest_bedrock_usage_normalizes():
    ingestor = BudgetIngestor(bedrock_client=DummyBedrockClient())
    metrics = ingestor.ingest_bedrock_usage(tenant_id="t_demo", timeframe="daily")
    assert metrics[0].vendor == "bedrock"
    assert metrics[0].model.startswith("anthropic")


def test_evaluate_call_allows_when_under_cap():
    svc = BudgetService(corridors={"t_demo": {"gemini": {"cap": 10.0}}})
    decision = svc.evaluate_call({"tenant_id": "t_demo"}, {"model": "gemini", "cost_estimate": 5.0})
    assert decision["decision"] == "allow"


def test_evaluate_call_warns_near_cap():
    svc = BudgetService(corridors={"t_demo": {"gemini": {"cap": 10.0}}})
    decision = svc.evaluate_call({"tenant_id": "t_demo"}, {"model": "gemini", "cost_estimate": 9.0})
    assert decision["decision"] == "needs_HITL"


def test_evaluate_call_denies_over_cap():
    svc = BudgetService(corridors={"t_demo": {"gemini": {"cap": 10.0}}})
    decision = svc.evaluate_call({"tenant_id": "t_demo"}, {"model": "gemini", "cost_estimate": 12.0})
    assert decision["decision"] == "deny"
