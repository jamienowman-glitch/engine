# Atomic Tasks: UIUnification

**Goal:** Establish a "Live" Workbench with real backend storage and enforcement.

## LANE 1: ENGINES (Northstar)

### [UNIFY-ENG-001] Create Firearms Registry Router
**Description:** Implement a router to manage `Firearm` definitions (acting as "License Types").
**Files:** `engines/firearms/routes.py`, `engines/firearms/models.py`.
**Endpoints:** `POST /registry/firearms/license_types` (Create), `GET /registry/firearms/license_types` (List).
**Acceptance:**
- Can create a new Firearm definition via API.
- List returns all definitions.
- `FirearmBinding` validation continues to work.

### [UNIFY-ENG-002] Create KPI Registry Metadata
**Description:** Update KPI data models to support "Category" and "Type" for UI grouping.
**Files:** `engines/kpi/models.py`.
**Changes:**
- Add `category_id: str` and `type_id: str` to `KpiDefinition`.
- OR create `KpiCategory` and `KpiType` models if strict relational integrity is needed (simpler: just fields).

### [UNIFY-ENG-003] Create KPI Registry Router
**Description:** Expose endpoints to list Categories and Types (derived from Definitions or explicit registry).
**Files:** `engines/kpi/routes.py`.
**Endpoints:** `GET /registry/kpi/categories`, `POST /registry/kpi/categories`.
**Acceptance:**
- UI can fetch categories to populate dropdowns.

### [UNIFY-ENG-004] Implement Workbench Router (Drafts)
**Description:** Create a router that wraps `VersionedStore` to allow saving/loading drafts.
**Files:** `engines/workbench/routes.py` (NEW), `engines/workbench/store.py`.
**Endpoints:** `PUT /workbench/drafts/{tool_name}`, `GET /workbench/drafts/{tool_name}`.
**Acceptance:**
- Saving a draft persists it to the in-memory store (or persistent backend if available).
- Loading retrieves the latest draft.

### [UNIFY-ENG-005] Implement Workbench Router (Publish)
**Description:** Expose the `Publisher` logic via API.
**Files:** `engines/workbench/routes.py` (NEW), `engines/workbench/publisher.py`.
**Endpoints:** `POST /workbench/publish`.
**Acceptance:**
- Returns `PortableMCPPackage` and `ActivationOverlay`.
- Successfully promotes a draft to a version in `VersionedStore`.

### [UNIFY-ENG-006] Wire Routers in Server
**Description:** Register the new routers in `engines/mcp_gateway/server.py` or the main engines server entrypoint.
**Files:** `engines/mcp_gateway/server.py` (or `engines/main.py`).
**Acceptance:**
- CURL tests to all new endpoints return 200/201.

## LANE 2: UI (Studio)

### [UNIFY-UI-001] Replace Firearms Mock with Real Client
**Description:** Update `WorkbenchClient` to call real Firearms Registry endpoints.
**Files:** `apps/studio/src/workbenchClient.ts`.
**Acceptance:**
- "Add License Type" in UI creates a real Firearm in Engines.
- Refreshing the page loads the list from Engines.

### [UNIFY-UI-002] Replace KPI Mock with Real Client
**Description:** Update `WorkbenchClient` to call real KPI Registry endpoints.
**Files:** `apps/studio/src/workbenchClient.ts`.
**Acceptance:**
- "Add Category" in UI creates a real Category in Engines.
- KPI dropdowns populate from backend data.

### [UNIFY-UI-003] Implement Real Draft Save/Load
**Description:** Switch `saveDraft` to hit `/workbench/drafts` and handle errors.
**Files:** `apps/studio/src/workbenchClient.ts`.
**Acceptance:**
- "Save" button persists state to Engines.
- Reloading the tool loads the draft from Engines.

### [UNIFY-UI-004] Implement Real Publish
**Description:** Switch `publish` to hit `/workbench/publish`.
**Files:** `apps/studio/src/workbenchClient.ts`.
**Acceptance:**
- Clicking Publish returns real package IDs.
- Success notification confirms version promotion.

### [UNIFY-UI-005] Add Firearms Blocking UI
**Description:** Handle 403 `firearms.license_required` errors from `tools/call`.
**Files:** `apps/studio/src/workbench/Workbench.tsx` (or where tool calls happen).
**Acceptance:**
- If user attempts to run a protected tool without a grant, UI displays a clear "License Required" error message referencing the specific license type.
