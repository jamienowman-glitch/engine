from pydantic import BaseModel, Field
from engines.common.identity import RequestContext
from engines.mcp_gateway.inventory import Tool, Scope

class PingInput(BaseModel):
    pass

class EchoInput(BaseModel):
    message: str = Field(..., description="Message to echo")

async def ping_handler(ctx: RequestContext, args: PingInput):
    return {"status": "ok", "message": "pong"}

async def echo_handler(ctx: RequestContext, args: EchoInput):
    return {"message": args.message}

def register(inventory):
    tool = Tool(
        id="echo",
        name="Echo Tool",
        summary="Simple echo utilities for testing."
    )
    
    tool.register_scope(Scope(
        name="echo.ping",
        description="Returns pong",
        input_model=PingInput,
        handler=ping_handler
    ))
    
    tool.register_scope(Scope(
        name="echo.echo",
        description="Echoes the input message",
        input_model=EchoInput,
        handler=echo_handler
    ))
    
    inventory.register_tool(tool)
