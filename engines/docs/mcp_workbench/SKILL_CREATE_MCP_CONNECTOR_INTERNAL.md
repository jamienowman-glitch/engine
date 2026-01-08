# SKILL: Create Internal MCP Connector

**Role:** Infrastructure Engineer / Agent
**Goal:** Expose an existing Engine (Muscle) as an MCP Connector.

## Prerequisites
1.  Target Engine must have `RequestContext` enforcement.
2.  Target Engine must have `ErrorEnvelope` normalization.
3.  You must have `admin` role in `t_system`.

## Step-by-Step Procedure

### Phase 1: Ingest & Define (Recon)
1.  **Identify Routes:** List all HTTP routes for the engine (e.g., `/video/render`).
2.  **Define Scopes:** Group routes by sensitivity.
    *   *Example:* `view` (GET), `act` (POST/PUT), `admin` (DELETE).
3.  **Create Draft:** Open Workbench -> "New Connector".
    *   ID: `video-render`
    *   Paste route definitions.

### Phase 2: Policy Attachment
4.  **Map Firearms:** For each scope, ask: "Does this move money, change data, or touch PII?"
    *   If YES -> Select `firearm.database_write` or similar.
    *   If HIGH RISK -> Check `Strategy Lock Required`.
5.  **Map KPIs:** Select which KPIs this tool affects (e.g., `gpu_cost`).
6.  **Review:** Verify no "Allowlists" are used (must use Firearms).

### Phase 3: Verification (Sandbox)
7.  **Click "Sandbox Test":** Workbench spins up an ephemeral instance.
8.  **Run Trigger:** Execute a sample `call_tool` request.
9.  **Verify Audit:** Check `EventSpine` for the audit log.
10. **Verify GateChain:** Ensure `SAFETY_DECISION` event was emitted.

### Phase 4: Publish
11. **Click "Publish":**
    *   Writes to `ComponentRegistry`.
    *   Writes to `FirearmsPolicyStore`.
12. **Verification URL:** Visit `/registry/specs/video-render` to confirm presence.

## Definition of Done (DoD)
*   [ ] Connector visible in Registry.
*   [ ] `GateChain` blocks call without Firearm.
*   [ ] `GateChain` allows call with Firearm.
*   [ ] Usage logged to Budget/KPI.
