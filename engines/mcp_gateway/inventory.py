from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Awaitable, Type

from pydantic import BaseModel

from engines.common.identity import RequestContext
from engines.mcp_gateway.schema_gen import generate_json_schema

@dataclass
class Scope:
    name: str # e.g. "echo.ping"
    description: str
    input_model: Type[BaseModel]
    handler: Callable[[RequestContext, BaseModel], Awaitable[Any]]
    # Policy tags could go here (e.g. firearms_required=True)
    firearms_required: bool = False
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return generate_json_schema(self.input_model)

@dataclass
class Tool:
    id: str # e.g. "echo"
    name: str
    summary: str
    scopes: Dict[str, Scope] = field(default_factory=dict)
    
    def register_scope(self, scope: Scope) -> None:
        self.scopes[scope.name] = scope

class Inventory:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register_tool(self, tool: Tool) -> None:
        self._tools[tool.id] = tool

    def clear(self) -> None:
        """Resets the inventory, clearing all registered tools."""
        self._tools.clear()

    def get_tool(self, tool_id: str) -> Optional[Tool]:
        return self._tools.get(tool_id)

    def list_tools(self) -> List[Tool]:
        return list(self._tools.values())
    
    def get_scope(self, tool_id: str, scope_name: str) -> Optional[Scope]:
        tool = self.get_tool(tool_id)
        if not tool:
            return None
        return tool.scopes.get(scope_name)

# Global inventory instance
_inventory = Inventory()

def get_inventory() -> Inventory:
    return _inventory
