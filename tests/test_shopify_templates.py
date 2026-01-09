import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.shopify.impl import load_dynamic_tools, _execute_graphql

def test_shopify_dynamic_tools_loading():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    # 1. Load Tools
    tools = load_dynamic_tools()
    print(f"Loaded Dynamic Tools: {[t.name for t in tools]}")
    
    assert len(tools) >= 4
    
    # Check "shopify_create_blog_post"
    blog_tool = next(t for t in tools if t.name == "shopify_create_blog_post")
    assert blog_tool.scopes["execute"] is not None
    
    # Check Handler Binding
    handler = blog_tool.scopes["execute"].handler
    assert callable(handler)

def test_shopify_dynamic_execution():
    asyncio.run(_async_test_shopify_dynamic_execution())

async def _async_test_shopify_dynamic_execution():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    # 1. Load & Get Tool
    tools = load_dynamic_tools()
    blog_tool = next(t for t in tools if t.name == "shopify_create_blog_post")
    handler = blog_tool.scopes["execute"].handler
    
    # 2. Create Payload (Pydantic)
    InputModel = blog_tool.scopes["execute"].input_model
    payload = InputModel(
        blog_id="gid://shopify/Blog/1",
        title="Dynamic Hello",
        image_url="http://img.com/a.jpg"
    )

    # 3. Exec with Mock
    with patch("engines.connectors.shopify.impl._execute_graphql", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"data": "ok"}
        
        await handler(ctx, payload)
        
        # Verify call
        mock_exec.assert_called_once()
        ca = mock_exec.call_args
        variables = ca[0][2]
        
        assert variables["blogId"] == "gid://shopify/Blog/1"
        assert variables["article"]["title"] == "Dynamic Hello"
