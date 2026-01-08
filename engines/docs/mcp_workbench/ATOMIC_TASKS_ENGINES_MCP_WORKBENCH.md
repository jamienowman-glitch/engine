# Atomic Tasks C1: Engines & MCP Workbench

**Goal:** Build the MCP Gateway, enable durable Workbench drafts, and support the "Vertical Slice".
**Priorities:** `BLOCKER` > `INTEGRATION` > `QUALITY`.

## Phase 1: Gateway Foundation (Based on MCP-ENG-01..05)

- [ ] **ENG-01: MCP Gateway Scaffold** `BLOCKER`
    - [ ] Create `engines/mcp_gateway/server.py` (FastAPI app).
    - [ ] Wire `engines.common.identity.RequestContextBuilder`.
    - [ ] Wire `engines.common.error_envelope.register_error_handlers`.
    - [ ] **Acceptance:** `GET /health` returns 200 and JSON with version. `curl -H "X-Mode: invalid"` returns canonical 400.

- [ ] **ENG-02: Tool Schema Gen (Multi-Scope)** `INTEGRATION`
    - [ ] Implement `engines/mcp_gateway/schema_gen.py`.
    - [ ] Input: Pydantic Model. Output: JSON Schema.
    - [ ] Requirement: Inventory must return `tool_id`, `scopes[]`, and `inputSchema` per scope.
    - [ ] **Acceptance:** Unit test: Convert multi-scope tool def to correct MCP discovery response.

- [ ] **ENG-03: Media V2 + Echo Wrapper (The Muscles)** `BLOCKER`
    - [ ] Create `engines/mcp_gateway/tools/echo.py` (Scope: `utility`, no firearms).
    - [ ] Create `engines/mcp_gateway/tools/media_v2.py`.
    - [ ] Implement at least TWO scopes for MediaV2 (e.g. `read` vs `write`).
    - [ ] **Acceptance:** `tools.call("media_v2.create_asset")` works. `tools.call("echo.ping")` works.

## Phase 2: Workbench Backend (New Enablers)

- [ ] **ENG-04: Workbench Draft Store** `BLOCKER`
    - [ ] Create `engines/workbench/drafts/service.py` using `VersionedStore`.
    - [ ] Resource Kind: `workbench_drafts`.
    - [ ] API: `save_draft`, `get_draft`, `list_drafts`.
    - [ ] **Acceptance:** Unit test: Save draft, verify version 1. Save again, verify version 2.

- [ ] **ENG-05: Sandbox Runner (The "Dry Run" Engine)** `BLOCKER`
    - [ ] Create `engines/workbench/sandbox/runner.py`.
    - [ ] Function: `run_sandbox_tool(ctx, tool_name, inputs, mock_policy=None)`.
    - [ ] Logic:
        1. Synthesize a "Sandbox Context" (derived from auth user).
        2. Run `GateChain` (mocking the policy check if `mock_policy` provided).
        3. Execute the internal tool wrapper (from ENG-03).
    - [ ] **Acceptance:** Run `media_v2.create_asset` via sandbox. Verify `GateChain` audit log is emitted.

- [ ] **ENG-06: Registry Writer (Two-Layer Publisher)** `INTEGRATION`
    - [ ] Create `engines/workbench/publisher/service.py`.
    - [ ] Logic:
        1. Write **Portable Package** (Spec + Schema) to `ComponentRegistry`.
        2. Write **Activation Overlay** (Firearms/KPI bindings) to `FirearmsPolicyStore` / other stores.
    - [ ] **Acceptance:** Functional test: Publish draft. Verify TWO distinct artifacts exist (Portable vs Overlay).

- [ ] **ENG-06b: MCP Client Connection Guide** `DX`
    - [ ] Create `engines/docs/mcp_workbench/GUIDE_CONNECT_REAL_CLIENT.md`.
    - [ ] Document: How to run gateway stdio/SSE.
    - [ ] Document: config for Claude Desktop / ChatGPT Dev Mode.
    - [ ] **Acceptance:** Use the doc to successfully connect a real client.

## Phase 3: Policy & Safety (Harden the Slice)

- [ ] **ENG-07: Firearms Binding Check (Per-Scope)** `SECURITY`
    - [ ] Update `GateChain` to call `FirearmsService.check_access`.
    - [ ] **Acceptance:**
        1. Bind `media.write` scope to `firearm.media.write`.
        2. Leave `media.read` scope unbound (open).
        3. Call `write` without firearm -> 403.
        4. Call `read` without firearm -> 200.
        5. Grant firearm -> Both 200.

- [ ] **ENG-08: KPI Mapping (Data)** `QUALITY`
    - [ ] Implement `engines/kpi/models.py:KpiBinding` (simple model).
    - [ ] Add `list_kpi_bindings(tool_name)` to `KpiService`.
    - [ ] **Acceptance:** Can save and retrieve a KpiBinding.

## Phase 4: Real Client Success (New)

- [ ] **ENG-09: Real MCP Client Verification** `QUALITY`
    - [ ] Create `engines/mcp_gateway/tests/repro_real_client.sh`.
    - [ ] Script: Boots server, mocks an MCP client handshake (stdio/SSE), lists tools, calls scope.
    - [ ] **Acceptance:** Script passes. Manual verification with Claude Desktop/ChatGPT also passes using ENG-06b guide.

## Vertical Slice Definition
*   **Repo:** `northstar-engines`
*   **Files:** `engines/mcp_gateway/*`, `engines/workbench/*`
*   **Success:**
    1.  Gateway runs in stdio/SSE mode.
    2.  Tools list shows `echo` and `media_v2`.
    3.  **Real MCP Client** can discover tools.
    4.  Client can call `echo` (success).
    5.  Client calls `media_v2` (fails 403 if no firearm).

## Diff Summary (Correction Run)
*   **Multi-Scope:** Updated ENG-02/03/07 to enforce tool scopes.
*   **Two-Layer:** Updated ENG-06 to split Portable vs Overlay.
*   **Real Client:** Added ENG-06b and ENG-09 to prove real-world connectivity.
*   **Echo Tool:** Added lightweight tool to ENG-03 for easier connectivity testing.
