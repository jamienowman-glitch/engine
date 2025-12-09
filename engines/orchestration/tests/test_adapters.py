from __future__ import annotations

from engines.orchestration.adapters import (
    AdkRuntimeAdapter,
    BedrockAgentsRuntimeAdapter,
    LangGraphRuntimeAdapter,
)
from engines.orchestration.schemas import AgentStepRequest, WorkflowRequest


class DummyClient:
    def __init__(self):
        self.calls = []

    def run_agent_step(self, request):
        self.calls.append(("step", request))
        return {"output": {"ok": True}, "traces": {"steps": 1}}

    def run_workflow(self, request):
        self.calls.append(("workflow", request))
        return {"output": {"wf": True}, "traces": {"nodes": 3}}

    def register_tool(self, tool_descriptor):
        self.calls.append(("register", tool_descriptor))

    def get_traces(self, run_id):
        self.calls.append(("get_traces", run_id))
        return {"id": run_id}

    def invoke_agent(self, request):
        self.calls.append(("invoke_agent", request))
        return {"output": {"ok": True}, "traces": {"steps": 2}}

    def invoke_workflow(self, request):
        self.calls.append(("invoke_workflow", request))
        return {"output": {"wf": True}, "traces": {"nodes": 4}}


def _req():
    return AgentStepRequest(agent_id="a1", input={"x": 1})


def _wf_req():
    return WorkflowRequest(workflow_id="wf1", graph_spec={}, inputs={})


def test_adk_adapter_proxies_calls():
    client = DummyClient()
    adapter = AdkRuntimeAdapter(client)
    res = adapter.run_agent_step(_req())
    assert res.output["ok"] is True
    wf = adapter.run_workflow(_wf_req())
    assert wf.output["wf"] is True
    adapter.register_tool({"id": "t1"})
    traces = adapter.get_traces("r1")
    assert traces["id"] == "r1"


def test_bedrock_adapter_proxies_calls():
    client = DummyClient()
    adapter = BedrockAgentsRuntimeAdapter(client)
    res = adapter.run_agent_step(_req())
    assert res.output["ok"] is True
    wf = adapter.run_workflow(_wf_req())
    assert wf.output["wf"] is True
    adapter.register_tool({"id": "t1"})
    traces = adapter.get_traces("r1")
    assert traces["id"] == "r1"


def test_langgraph_adapter_proxies_calls():
    client = DummyClient()
    adapter = LangGraphRuntimeAdapter(client)
    res = adapter.run_agent_step(_req())
    assert res.output["ok"] is True
    wf = adapter.run_workflow(_wf_req())
    assert wf.output["wf"] is True
    adapter.register_tool({"id": "t1"})
    traces = adapter.get_traces("r1")
    assert traces["id"] == "r1"
