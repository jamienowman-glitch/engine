from __future__ import annotations

from engines.orchestration.mapping import (
    build_agent_step_request,
    build_workflow_request,
    card_to_runtime_config,
    normalize_traces,
)


def _card():
    return {
        "agent_id": "agent-1",
        "workflow_id": "wf-1",
        "models": {"primary": "gemini"},
        "tools": [{"id": "tool-1"}],
        "safety": {"guardrails": True},
        "vendor": "adk",
        "cost_tier": "core",
        "graph_spec": {"nodes": []},
    }


def test_card_to_runtime_config():
    cfg = card_to_runtime_config(_card())
    assert cfg["models"]["primary"] == "gemini"
    assert cfg["tools"][0]["id"] == "tool-1"


def test_build_agent_step_request():
    req = build_agent_step_request(_card(), {"x": 1, "episode_id": "ep1"})
    assert req.agent_id == "agent-1"
    assert req.context["vendor"] == "adk"
    assert req.episode_id == "ep1"


def test_build_workflow_request():
    req = build_workflow_request(_card(), {"foo": "bar", "episode_id": "ep2"})
    assert req.workflow_id == "wf-1"
    assert req.inputs["foo"] == "bar"
    assert req.context["cost_tier"] == "core"


def test_normalize_traces_passthrough():
    native = {"trace": {"steps": 2}}
    assert normalize_traces(native)["raw"] == native
