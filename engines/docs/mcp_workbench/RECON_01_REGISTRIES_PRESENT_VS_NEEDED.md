# RECON 01: Registries Present vs. Needed

## Existing Registries

| Name | Route / Resource Kind | Storage Class | Current Contents |
| :--- | :--- | :--- | :--- |
| **Specs Registry** | `component_registry` | `TabularStore` | `atom`, `component`, `lens` specs. |
| **Firearms Policy** | `firearms_policy_store` | `TabularStore` | `Firearm` definitions, `FirearmGrant` assignments, `FirearmBinding` (action -> firearm). |
| **Strategy Lock** | `strategy_lock` | `TabularStore` | Lock policies and active lock states. |
| **KPI Registry** | `kpi_store` | `TabularStore` | `KpiDefinition`, `KpiCorridor` (thresholds). |
| **Budget Usage** | `budget_usage_store` | `TabularStore` | Usage events (cost tracking). Note: Policy config often in code or separate config repo/store. |
| **Routing Registry** | `routing_config` | `TabularStore` (or File) | Backend routing configurations (resource_kind -> backend_type). |

## Implied / Needed Registries for Workbench

To support the "Connector Workbench" workflow, we need to map the following concepts to storage:

| Concept | Recommended Storage | Notes |
| :--- | :--- | :--- |
| **MCP Connector Definition** | **Specs Registry** (`kind=component`) | Use `metadata.spec_class="mcp_connector"`. Store portability metadata here. |
| **Atomic Scopes** | **Specs Registry** (inside Connector) | Store scopes as a list within the Connector definition `schema` or `metadata`. |
| **Firearms Requirements** | **Firearms Policy Store** (`FirearmBinding`) | Map `action_name` (tool/scope) to `firearm_id`. Already supported by `FirearmBinding`. |
| **KPI Mappings** | **New / KPI Store Extension** | Need a way to map "tool usage" -> "KPI metric". Could be part of Connector Def or a new `KpiBinding`. |
| **Draft Connectors** | **VersionedStore** (`resource_kind="workbench_drafts"`) | For "in-progress" work before publishing to Specs Registry. |
| **Skills / Walkthroughs** | **Docs / Artifact Store** | Markdown files describing how to use the tool. Could be blobs in `media_v2` or entries in Specs Registry (`kind=curriculum`?). |
| **Packaging Config** | **Specs Registry** (inside Connector) | Metadata for `npx` publish (package name, version, etc.). |

## Gap Analysis

1.  **KPI Mapping:** No explicit "Tool -> KPI" binding store exists. We verify `list_corridors` but that defines *what* the KPI is, not *which tool affects it*.
    *   *Recommendation:* Add `KpiToolBinding` or similar to the Workbench Data Model.
2.  **Billing Extensions:** No runtime entitlement store found.
    *   *Strategy:* Define strictly as "Missing Dependency".
