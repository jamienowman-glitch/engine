import pytest
from engines.workbench.models import (
    ToolDefinition, MetricDefinition, 
    ScopeOverlay, UTMConfig, BudgetConfig, 
    PolicyConfig, NorthstarActivationOverlay, ToolOverlay
)

def test_tool_definition_metrics():
    """Test Layer 1 ToolDefinition with Metrics."""
    tool = ToolDefinition(
        id="conn.test",
        name="Test Tool",
        summary="A test tool",
        scopes={},
        metrics=[
            MetricDefinition(name="orders", description="Order Count", unit="count")
        ]
    )
    assert len(tool.metrics) == 1
    assert tool.metrics[0].name == "orders"
    assert tool.metrics[0].unit == "count"

def test_scope_overlay_configs():
    """Test Layer 2 ScopeOverlay with UTM and Budget."""
    overlay = ScopeOverlay(
        policy=PolicyConfig(firearms=True),
        utm_config=UTMConfig(platform="shopify", content_type="product"),
        budget_config=BudgetConfig(cost_per_call=0.05, free_tier_daily_cap=50)
    )
    
    assert overlay.policy.firearms is True
    assert overlay.utm_config.platform == "shopify"
    assert overlay.budget_config.cost_per_call == 0.05
    assert overlay.budget_config.free_tier_daily_cap == 50

def test_defaults():
    """Ensure backward compatibility with defaults."""
    overlay = ScopeOverlay()
    assert overlay.policy is None
    assert overlay.utm_config is None
    assert overlay.budget_config is None

    tool = ToolDefinition(id="t1", name="n1", summary="s1", scopes={})
    assert tool.metrics == []

def test_full_overlay_structure():
    """Test deep structure nesting."""
    activ = NorthstarActivationOverlay(
        package_id="pkg.1",
        package_version="1.0.0",
        tools={
            "t1": ToolOverlay(
                scopes={
                    "read": ScopeOverlay(
                         budget_config=BudgetConfig(free_tier_daily_cap=10)
                    )
                }
            )
        }
    )
    
    assert activ.tools["t1"].scopes["read"].budget_config.free_tier_daily_cap == 10
