import pytest
from unittest.mock import MagicMock
from engines.workbench.publisher import PublisherService
from engines.workbench.models import PortableMCPPackage, NorthstarActivationOverlay, ToolDefinition, ToolOverlay, ScopeOverlay, PolicyConfig
from engines.common.identity import RequestContext

def test_publish_flow():
    # Mocks
    registry = MagicMock()
    firearms = MagicMock()
    kpi = MagicMock()
    
    svc = PublisherService(registry=registry, firearms=firearms, kpi=kpi)
    
    ctx = RequestContext(tenant_id="t_demo", mode="lab", project_id="p1")
    
    # Data
    pkg = PortableMCPPackage(
        id="com.example.tool",
        version="1.0.0",
        name="Example Tool",
        description="A test tool",
        tools=[
            ToolDefinition(
                id="tool_a",
                name="Tool A",
                summary="Does A",
                scopes={"read": {}, "write": {}}
            )
        ]
    )
    
    overlay = NorthstarActivationOverlay(
        package_id="com.example.tool",
        package_version="1.0.0",
        tools={
            "tool_a": ToolOverlay(
                scopes={
                    "write": ScopeOverlay(
                        policy=PolicyConfig(
                            firearms=True,
                            required_licenses=["lic_nuke"]
                        )
                    )
                }
            )
        }
    )
    
    # Act
    svc.publish(ctx, pkg, overlay)
    
    # Assert
    # 1. Registry called?
    registry.save_component.assert_called_once()
    saved_comp = registry.save_component.call_args[0][1]
    assert saved_comp["id"] == "com.example.tool"
    assert saved_comp["metadata"]["spec_class"] == "mcp_connector"
    
    # 2. Firearms called?
    firearms.bind_action.assert_called_once() # Only for 'write' scope
    binding = firearms.bind_action.call_args[0][1]
    assert binding.action_name == "tool_a.write"
    assert binding.firearm_id == "lic_nuke"
