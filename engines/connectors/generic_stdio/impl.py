from __future__ import annotations
import os
from typing import Dict, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class StdioMCPAdapter:
    """
    Adapter for connecting to Stdio-based MCP servers.
    Follows a 'Stateless' pattern: Spawns process, executes, closes.
    """
    def __init__(self, command: str, args: list[str] = None, env: Dict[str, str] = None):
        self.command = command
        self.args = args or []
        self.env = env or {}
        # Merge with current env to ensure PATH is correct for npx etc
        self.full_env = os.environ.copy()
        if env:
            self.full_env.update(env)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.full_env
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # We assume the tool exists. 
                # In a robust implementation we might list_tools to validate first,
                # but for speed, we just call.
                
                result = await session.call_tool(tool_name, arguments)
                return result

    async def list_tools(self) -> Any:
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.full_env
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.list_tools()
