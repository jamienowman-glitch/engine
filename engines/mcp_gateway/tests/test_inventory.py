import pytest
from pydantic import BaseModel, Field
from engines.mcp_gateway.inventory import Inventory, Tool, Scope
from engines.mcp_gateway.schema_gen import generate_json_schema
from engines.common.identity import RequestContext

class TestInput(BaseModel):
    message: str = Field(..., description="The message to echo")

async def dummy_handler(ctx: RequestContext, args: TestInput):
    return {"echo": args.message}

def test_schema_gen():
    schema = generate_json_schema(TestInput)
    assert schema["type"] == "object"
    assert "message" in schema["properties"]
    assert schema["properties"]["message"]["description"] == "The message to echo"

def test_inventory_registration():
    inventory = Inventory()
    tool = Tool(id="test_tool", name="Test Tool", summary="A test tool")
    
    scope = Scope(
        name="test.echo",
        description="Echoes back",
        input_model=TestInput,
        handler=dummy_handler
    )
    
    tool.register_scope(scope)
    inventory.register_tool(tool)
    
    retrieved = inventory.get_tool("test_tool")
    assert retrieved is not None
    assert retrieved.name == "Test Tool"
    assert "test.echo" in retrieved.scopes
    
    retrieved_scope = inventory.get_scope("test_tool", "test.echo")
    assert retrieved_scope is not None
    assert retrieved_scope.name == "test.echo"
    assert retrieved_scope.input_schema["properties"]["message"]["type"] == "string"
