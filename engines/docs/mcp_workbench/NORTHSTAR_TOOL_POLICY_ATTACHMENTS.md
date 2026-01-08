# CONTRACT B2: Northstar Policy Attachments (Internal)

This document defines how a **Portable MCP Connector** becomes an **Active Internal Muscle**.
Policy Attachments are the "glue" that binds a generic tool to Northstar's strict safety, logging, and billing requirements.

## 1. The Attachment Model

Stored in `FirearmsPolicyStore` (for safety) and `KpiStore` (for metrics).
Keyed by `{tenant_id}#{mode}#{env}#binding#{tool_name}`.

### A. Firearms Binding (Safety)

**Store:** `FirearmsRepository` -> `firearms_policy_store`
**Model:** `FirearmBinding`

```python
class FirearmBinding(BaseModel):
    action_name: str         # e.g., "mcp.github.create_issue"
    firearm_id: str          # e.g., "firearm.external_write"
    strategy_lock_required: bool  # Enforced by GateChain
```

*   **Enforcement:**
    *   `GateChain` calls `FirearmsService.check_access(ctx, action_name)`.
    *   If `action_name` has a binding, the actor (Agent/User) **MUST** hold a `FirearmGrant` for `firearm_id`.
    *   If `strategy_lock_required=True`, `GateChain` also demands `StrategyLock` resolution (often human approval).

### B. KPI Mapping (Metrics)

**Store:** `KpiBinding` (New / Proposed)
**Goal:** Map tool usage to business KPIs.

```json
{
  "tool_name": "mcp.openai.gpt4_complete",
  "kpi_impact": [
    {
      "kpi_name": "model_spend_daily",
      "impact_type": "cost",
      "formula": "usage.cost * 1.0"
    },
    {
      "kpi_name": "ai_generated_tokens",
      "impact_type": "count",
      "formula": "usage.total_tokens"
    }
  ]
}
```

### C. Routing Configuration

**Store:** `RoutingRegistry`
**Goal:** Ensure the connector uses the correct backend for its persistence/state.

*   **Requirement:** Every internal MCP tool must declare its dependency on `TabularStore` or `ObjectStore`.
*   **Validation:** `engines/routing/manager.py` startup check ensures these routes exist for the current tenant.

### D. Billing / Entitlements

**Status:** MISSING DEPENDENCY
**Requirement:** `EntitlementService.check_entitlement(ctx, feature_id="connector.github")`.
**Temporary Workaround:** Use `Firearm` as a proxy for entitlement (i.e., you can't get the gun if you didn't buy the license).

## 2. Activation Flow

1.  **Ingest:** Load Portable MCP Contract.
2.  **Attach Policy:** Admin/Architect configures Firearms, KPI, Routing via Workbench.
3.  **Activate:** Save Policies to Registries (`FirearmsPolicyStore`, `KpiStore`).
4.  **Run:** `GateChain` now enforces these policies on every call.
