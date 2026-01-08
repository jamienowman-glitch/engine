# EXECUTIVE SUMMARY: MCP + Connector Workbench

**Objective:** Enable "Connector Workbench" — A UI for Architects to safely expose internal Muscles and external APIs as **atomic, policy-guarded MCP tools**.

## 1. What Exists (The Foundation)
*   **Identity Control:** `RequestContext` strictly enforces `X-Mode` (SaaS/Ent/Lab) and `X-Tenant-Id`.
*   **Safety Layer:** `GateChain` centralizes safety checks (Firearms, Strategy Lock, Budget, KPI).
*   **Policy Stores:** `FirearmsPolicyStore`, `KpiStore`, and `StrategyLockStore` are already routed and durable.
*   **Registry:** `ComponentRegistry` exists and supports versions. `VersionedStore` supports durable drafts.
*   **Muscles:** `media_v2`, `video_render`, `chat_service` are ready to be wrapped.

## 2. What's Missing (The Gap)
*   **MCP Gateway:** No runtime exists to speak the MCP protocol (Stdio/SSE).
*   **Workbench UI:** No UI exists to ingest specs, map scopes, or bind firearms.
*   **Draft Store:** `VersionedStore` exists but isn't wired for "Workbench Drafts".
*   **Sandbox:** No "Dry Run" engine exists to test tools without publishing.

## 3. Build Order: The Vertical Slice
To prove the system works, we will build a slice covering **Ingest -> Policy -> Save -> Run**.

1.  **Engine Foundation (`BLOCKER`):** Scaffold `engines/mcp_gateway`. Wire Identity and Error Envelopes.
2.  **Workbench Backend (`Enabler`):** Implement `DraftStore` (VersionedStore) and `SandboxRunner` (GateChain without execution).
3.  **UI Shell (`DX`):** Simple "Paste JSON + Map Policy + Save" interface.
4.  **The Muscle (`Media V2`):** Wrap `media_v2.create_asset` as the first internal MCP tool.
5.  **Verification:** User creates draft for `media_v2`, binds `firearm.media.write`, runs sandbox, and publishes.

## 4. The Next 20 Connectors
After the vertical slice, we will onboard these high-value muscles/connectors:

1.  `chat_service` (Append Message)
2.  `video_render` (Submit Job)
3.  `vector_explorer` (Ingest File)
4.  `storage_object` (Presign Upload)
5.  `google_drive` (External - Read)
6.  `github` (External - Issues)
7.  `slack` (External - Post Message)
8.  `postgres` (External - Query)
9.  `linear` (External - Issues)
10. `notion` (External - Search)
11. `audio_transcribe` (Muscle)
12. `audio_synthesize` (Muscle)
13. `image_generate` (Muscle)
14. `kpi_reporter` (Muscle - Read Stats)
15. `budget_alert` (Muscle - Read Cost)
16. `user_profile` (System - Read)
17. `feature_flags` (System - Toggle)
18. `firearms_admin` (System - Grant)
19. `registry_browser` (System - List)
20. `smtp_mailer` (External - Send)

## Recommendation
**Do NOT implement code yet.** Approve the Contracts (B-Series) and Task Plans (C-Series) first.
The Recon confirms that `northstar-engines` has 90% of the primitives needed; the work is largely **integration and wiring**, not new invention.
