# RECON 00: Integration Points Map

| Capability | Repo Location | Integration Point / Usage Pattern | Notes |
| :--- | :--- | :--- | :--- |
| **Identity & Request Context** | `engines/common/identity.py` | `RequestContext` (class), `RequestContextBuilder` (headers -> ctx), `validate_identity_precedence` | Enforces `X-Mode`, `X-Tenant-Id` and rejects `X-Env`. Central identity truth. |
| **Routing Manager** | `engines/routing/manager.py` | `startup_validation_check`, `get_route_config` | Enforces backend presence at startup. `fail-fast` logic for sellable modes. |
| **Routing Registry** | `engines/routing/registry.py` | `routing_registry()` singleton | Access to raw routing table. |
| **Durable Registry Storage** | `engines/registry/repository.py` | `ComponentRegistryRepository` | Underlying storage for `atom`, `component`, `lens`. Uses `TabularStoreService`. |
| **Durable Drafts** | `engines/storage/versioned_store.py` | `VersionedStore(ctx, resource_kind="...", scope_config=...)` | Supports `save_new`, `bump_version`, `get_latest`. Scoped to tenant/project/user/surface/app. |
| **Firearms Policy Store** | `engines/firearms/repository.py` | `RoutedFirearmsRepository` (uses `firearms_policy_store`) | `create_binding`, `get_binding`. Stores `FirearmBinding` and `FirearmGrant`. |
| **Firearms Enforcement** | `engines/firearms/service.py` | `FirearmsService.check_access(ctx, action_name)` | Returns `FirearmDecision` (allowed/block + reason). |
| **Strategy Lock Store** | `engines/strategy_lock/repository.py` | `StrategyLockRepository` | Stores lock policies and states. |
| **Strategy Lock Resolution** | `engines/strategy_lock/service.py` | `StrategyLockService.resolve_strategy_lock(ctx, ...)` | Determines if human approval is required. |
| **KPI Store & API** | `engines/kpi/service.py`, `engines/kpi/routes.py` | `KpiService` | `list_definitions`, `list_corridors`, `record_raw_measurement`. |
| **Budget Store & API** | `engines/budget/service.py` | `BudgetService`, `BudgetUsageRepository` | `record_usage`, `summary`. Uses `StorageClass.COST`. |
| **Event Spine** | `engines/event_spine` | `EventSpineService` (implied by usage in `VersionedStore` or similar layers) | Emits audit/spine events. |
| **GateChain** | `engines/nexus/hardening/gate_chain.py` | `GateChain.run(ctx, action, ...)` | Central safety enforcement loop (Firearms -> StratLock -> Budget -> KPI -> Temp -> Audit). |
| **Billing / Entitlements** | *Missing / Not Found* | *None* | Treat as **MISSING DEPENDENCY**. Runtime entitlement hook needs to be defined. |

## Key Findings

1.  **Identity is strict:** `RequestContext` is the only way to pass identity. It strictly validates `X-Mode` and rejects `X-Env`.
2.  **Persistence is routed:** Everything uses `TabularStoreService` via specific repositories (`FirearmsRepository`, `ComponentRegistryRepository`, `VersionedStore`).
3.  **Safety is centralized:** `GateChain` is the canonical place where policies are checked in sequence.
4.  **Drafts are supported:** `VersionedStore` provides exactly the "save draft" capability needed for the Workbench, with versioning built-in.
