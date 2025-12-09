"""Agent runtime adapter interfaces and mockable implementations."""
from __future__ import annotations

from typing import Any, Dict, List, Protocol

from engines.orchestration.schemas import (
    AgentStepRequest,
    AgentStepResult,
    WorkflowRequest,
    WorkflowResult,
)


class AgentRuntimeAdapter(Protocol):
    """Base interface for agent runtimes."""

    def run_agent_step(self, request: AgentStepRequest) -> AgentStepResult:
        ...

    def run_workflow(self, request: WorkflowRequest) -> WorkflowResult:
        ...

    def register_tool(self, tool_descriptor: Dict[str, Any]) -> None:
        ...

    def get_traces(self, run_id: str) -> Dict[str, Any]:
        ...


class AdkRuntimeAdapter:
    def __init__(self, client: Any) -> None:
        self._client = client

    def run_agent_step(self, request: AgentStepRequest) -> AgentStepResult:
        response = self._client.run_agent_step(request)
        return AgentStepResult(output=response.get("output", {}), traces=response.get("traces", {}))

    def run_workflow(self, request: WorkflowRequest) -> WorkflowResult:
        response = self._client.run_workflow(request)
        return WorkflowResult(output=response.get("output", {}), traces=response.get("traces", {}))

    def register_tool(self, tool_descriptor: Dict[str, Any]) -> None:
        self._client.register_tool(tool_descriptor)

    def get_traces(self, run_id: str) -> Dict[str, Any]:
        return self._client.get_traces(run_id)


class BedrockAgentsRuntimeAdapter:
    def __init__(self, client: Any) -> None:
        self._client = client

    def run_agent_step(self, request: AgentStepRequest) -> AgentStepResult:
        response = self._client.invoke_agent(request)
        return AgentStepResult(output=response.get("output", {}), traces=response.get("traces", {}))

    def run_workflow(self, request: WorkflowRequest) -> WorkflowResult:
        response = self._client.invoke_workflow(request)
        return WorkflowResult(output=response.get("output", {}), traces=response.get("traces", {}))

    def register_tool(self, tool_descriptor: Dict[str, Any]) -> None:
        self._client.register_tool(tool_descriptor)

    def get_traces(self, run_id: str) -> Dict[str, Any]:
        return self._client.get_traces(run_id)


class LangGraphRuntimeAdapter:
    def __init__(self, client: Any) -> None:
        self._client = client

    def run_agent_step(self, request: AgentStepRequest) -> AgentStepResult:
        response = self._client.run_agent_step(request)
        return AgentStepResult(output=response.get("output", {}), traces=response.get("traces", {}))

    def run_workflow(self, request: WorkflowRequest) -> WorkflowResult:
        response = self._client.run_workflow(request)
        return WorkflowResult(output=response.get("output", {}), traces=response.get("traces", {}))

    def register_tool(self, tool_descriptor: Dict[str, Any]) -> None:
        self._client.register_tool(tool_descriptor)

    def get_traces(self, run_id: str) -> Dict[str, Any]:
        return self._client.get_traces(run_id)
