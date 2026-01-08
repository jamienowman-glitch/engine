# Unification Gap Report: Connector Workbench

**Date:** 2026-01-07
**Scope:** UI (Studio) <-> Engines (Northstar)
**Author:** Unification Architect

## Executive Summary
The Connector Workbench UI is currently operating in a semi-detached state. While the MCP Inventory read path is "real" (hitting `/tools/list`), all write paths (saving drafts, publishing, creating registry items) are mocked in `workbenchClient.ts`. On the Engines side, the core logic for enforcement (Firearms, KPI, GateChain) is robust, but the specific **Management APIs** required by the Workbench (Drafts CRUD, Registry CRUD) are either missing, unwired, or possess data model mismatches.

## 1. UI Current State (The "Mock" Reality)
The `WorkbenchClient` in `apps/studio` is heavily mocked.

| Feature | UI Call (Intended) | Real Status | Backend Handler |
| :--- | :--- | :--- | :--- |
| **Inventory** | `GET /mcp/inventory/tools` | **REAL** | `mcp_gateway.server:list_tools` |
| **Drafts** | `PUT /workbench/drafts/:tool` | **MOCK** | `engines.workbench.routes:save_draft` |
| **Publish** | `POST /workbench/publish` | **MOCK** | `engines.workbench.routes:publish_tool` |
| **Firearms** | `GET /registry/firearms/license-types` | **MOCK** | `engines.firearms.registry_routes:list_license_types` |
| **KPI Cat** | `GET /registry/kpi/categories` | **MOCK** | `engines.kpi.registry_routes:list_categories` |
| **KPI Type** | `GET /registry/kpi/types` | **MOCK** | `engines.kpi.registry_routes:list_types` |
| **KPI Bind** | `PUT /registry/kpi/bindings` | **MOCK** | *Missing Route* |

## 2. Engines Current State (The "Enforcement" Reality)
Engines has the *capability* to support the Workbench but lacks the specific *API Surface*.

### A. Missing Routes (Unwired Code)
- **Drafts Store:** `VersionedStore` exists in `engines.storage`, but no Router exposes it.
- **Publisher:** `Publisher` class exists in `engines.workbench`, but no Router exposes it.
- **Firearms Registry:** `FirearmsService` manages `Bindings` (Policy) and `Grants`, but has no CRUD for `Firearm` definitions (which UI calls "License Types").
- **KPI Registry:** `KpiService` manages `Definitions` and `Corridors`, but has no concept of "Categories" or "Types" in its model, nor endpoints to list them.

### B. Data Model Mismatches
1.  **KPIs:**
    - **UI Expects:** `KPICategory` (e.g. "Performance") + `KPIType` (e.g. "Latency").
    - **Engines Has:** `KpiDefinition` (flattened metric).
    - **Gap:** Need to either add `category/type` fields to `KpiDefinition` or create a lightweight registry for these groupings.

2.  **Firearms:**
    - **UI Expects:** "License Types" (Definitions of capabilities).
    - **Engines Has:** `Firearm` entity (matches "License Type" semantically) but no CRUD API.

## 3. Top-Level Gaps
1.  **Workbench Router Missing:** No endpoint to accept `PUT /workbench/drafts` or `POST /workbench/publish`.
2.  **Registry Routers Missing:** No endpoint to listing/creating standard Firearms License Types or KPI Categories.
3.  **Enforcement Bypass:** UI currently mocks "Publish" so it never actually generates the `PortableMCPPackage` or `ActivationOverlay` needed for the two-layer enforcement system.

## 4. Status (2026-01-07)
**ALL CRITICAL GAPS RESOLVED.**
- [x] **Registry: Firearms**: Missing `list_license_types` and `create_license_type`. **RESOLVED**
- [x] **Registry: KPI**: Missing `KpiCategory` and `KpiType` models and CRUD. **RESOLVED**
- [x] **Workbench: Drafts**: No API to save/load drafts. `VersionedStore` was in-memory only. **RESOLVED**
- [x] **Workbench: Publish**: No API to publish. Publisher logic existed but not exposed. **RESOLVED**
- [x] **Enforcement**: Wiring required to ensure all paths hit `GateChain`. **RESOLVED**
