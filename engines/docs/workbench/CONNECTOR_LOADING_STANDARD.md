# Connector Loading Standard

**Authority**: Northstar Engines & Workbench  
**Enforcement**: Use `engines/connectors/` ONLY.  
**Pattern**: "One Folder Per Connector"

## 1. Directory Structure

All MCP connectors must live in `engines/connectors/<tool_id>/`.
The structure is strict:

```text
engines/connectors/
  ├── <tool_id>/              # e.g. "github", "jira", "postgres"
  │   ├── __init__.py         # Must expose `register_connector()`
  │   ├── connector.py        # The class implementation (logic)
  │   ├── README.md           # Instructions specific to this connector
  │   └── tests/              # (Optional) Unit tests for this connector
```

## 2. The `__init__.py` Contract

Every connector MUST expose a single entry point in its `__init__.py`:

```python
# engines/connectors/my_tool/__init__.py

def register_connector():
    from .connector import MyToolConnector
    from engines.mcp_gateway.inventory import get_inventory
    # Registration logic here
    # ...
```

## 3. Loading Mechanisms (The "One True Way")

The `inventory.py` (or loader service) MUST NOT hardcode imports.
It supports two loading strategies:

### A. Config-Driven (Current / Lab)
Inventory reads `ENGINES_EnabledConnectors` (list of strings) from env/config.
It iterates the list, imports the module `engines.connectors.<tool_id>`, and calls `register_connector()`.

### B. Registry-Driven (Future / Enterprise)
Inventory queries `ComponentRegistry` for enabled connectors > imports modules > registers.

## 4. Agent Constraints

**Agents (Jules/Code-Pro) are ALLOWED to:**
- Create `engines/connectors/<new_tool_id>/`
- Edit files INSIDE that folder.

**Agents are FORBIDDEN from:**
- Editing `engines/mcp_gateway/inventory.py` (No manual imports!)
- Editing `engines/common/**`
- Adding top-level exports to `engines/__init__.py`

## 5. Security & Policy
- **No Policy in Code**: Connectors must NOT set `firearms_required=True` in code *unless* it is an inherent property of the code (e.g. `implementation_mode` writes files). Even then, the Overlay is the authority.
- **No Allowlists**: Never hardcode user IDs or "allowed_users". Use `required_license_types` (AuthZ Service).
