from __future__ import annotations
import csv
import io
from typing import List

from engines.mcp_gateway.inventory import get_inventory
from engines.firearms.service import get_firearms_service
from engines.common.identity import RequestContext

# NOTE: Since firearms bindings are via repository/store which requires Context,
# exporting ALL policies might be tricky if they are tenant-scoped.
# However, FirearmBinding in Phase 3 logic implies global tool definitions for now.
# But `FirearmsRepository` is usually tenant-isolated.
# For this export, we will iterate the INVENTORY (which is global code-based)
# and check bindings for each scope using a system context.

def export_tools_tsv() -> str:
    inventory = get_inventory()
    output = io.StringIO()
    writer = csv.writer(output, delimiter='\t')
    writer.writerow(["tool_id", "name", "summary"])
    
    for tool in inventory.list_tools():
        writer.writerow([tool.id, tool.name, tool.summary])
        
    return output.getvalue()

def export_scopes_tsv() -> str:
    inventory = get_inventory()
    output = io.StringIO()
    writer = csv.writer(output, delimiter='\t')
    writer.writerow(["tool_id", "scope_name", "description"])
    
    for tool in inventory.list_tools():
        for scope in tool.scopes.values():
            writer.writerow([tool.id, scope.name, scope.description])
            
    return output.getvalue()

def export_policies_tsv(ctx: RequestContext) -> str:
    """
    Export Firearms requirements for all scopes in Inventory.
    Requires a valid context to check bindings against the repo.
    """
    inventory = get_inventory()
    firearms = get_firearms_service()
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter='\t')
    writer.writerow(["tool_id", "scope_name", "requires_firearms", "license_types", "strategy_lock"])
    
    for tool in inventory.list_tools():
        for scope_name in tool.scopes.keys():
            action_name = f"{tool.id}.{scope_name}"
            # Check binding
            # Repo method `get_binding` takes (ctx, action_name)
            binding = firearms.repo.get_binding(ctx, action_name)
            
            if binding:
                writer.writerow([
                    tool.id, 
                    scope_name, 
                    "True", 
                    binding.firearm_id, # Simplified: 1 license
                    str(binding.strategy_lock_required)
                ])
            else:
                writer.writerow([tool.id, scope_name, "False", "", "False"])

    return output.getvalue()
