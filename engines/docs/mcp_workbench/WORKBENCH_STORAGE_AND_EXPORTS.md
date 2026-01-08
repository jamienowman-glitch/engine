# CONTRACT B3: Workbench Data Model & Storage

## 1. Data Model: Drafts vs. Published

The Workbench uses a "Draft -> Publish" lifecycle.

### Drafts (The Workbench Workspace)
*   **Store:** `VersionedStore(ctx, resource_kind="workbench_drafts", scope_config={tenant, user})`
*   **Persistence:** Durable on every "Save". No in-memory drafts.
*   **Schema:** `WorkbenchDraft`
    ```json
    {
      "id": "draft_abc123",
      "connector_id": "github-connector",
      "stage": "definition", // definition, scoping, policy, verification
      "spec_snapshot": { ... }, // The MCP Contract
      "policy_snapshot": {      // The Internal Policy
        "firearms": { ... },
        "kpis": { ... }
      }
    }
    ```

### Published (The Live System)
*   **Connector Spec:** `ComponentRegistry` (`kind=component`)
*   **Policies:** `FirearmsPolicyStore`, `KpiStore`
*   **Transition:** "Publish" button transactionally writes to all Registries and marks Draft as `status="published"`.

## 2. Card View Fields

When viewing a Connector in the Workbench UI:

| Field | Source | Editable? |
| :--- | :--- | :--- |
| **Name/ID** | `spec.id` | No (after creation) |
| **Version** | `spec.version` | Yes (bump) |
| **Scopes** | `spec.scopes` | Yes (if draft) |
| **Firearms** | `policy.firearms` | Yes |
| **KPIs** | `policy.kpis` | Yes |
| **Validation** | Sandbox Result | Read-only |

## 3. TSV Export Schemas

For "Google Sheets" interoperability.

### A. Connector Registry Export
`connector_id` | `version` | `scope_count` | `firearms_required` | `published_at`
--- | --- | --- | --- | ---
`github` | `1.2.0` | `2` | `TRUE` | `2026-01-07T12:00:00Z`

### B. Policy Matrix Export
`connector_id` | `scope` | `firearm_id` | `strategy_lock`
--- | --- | --- | ---
`github` | `admin_write` | `firearm.external_write` | `TRUE`
`github` | `read_public` | `NONE` | `FALSE`

### C. Coverage Reports
`engine_route` | `mcp_wrapper_status` | `policy_coverage`
--- | --- | ---
`/chat/*` | `DONE` | `100%`
`/video/*` | `MISSING` | `0%`
