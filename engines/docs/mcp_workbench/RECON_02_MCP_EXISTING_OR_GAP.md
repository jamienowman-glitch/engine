# RECON 02: MCP Existing vs Gap

## Current State

*   **No Active MCP Gateway:** There is no running MCP server or gateway in `northstar-engines` or `northstar-agents`.
*   **Feasibility Study Exists:** `docs/mcp_recon/MCP_RECON_02_MCP_GATEWAY_FEASIBILITY.md` outlines a viable plan.
*   **Muscle Readiness:** Core muscles (`media_v2`, `video_render`, `chat`) are partially ready but lack consistent schema exposure.
*   **Tool Gateway:** No centralized "Tool Gateway" exists. Tools are currently just HTTP endpoints called by ad-hoc clients.

## The Gap

To achieve "Connector Workbench", we are missing:

1.  **The MCP Host:** A FastAPI app (sibling to `engines`) that implements the MCP protocol (SSE/Stdio).
2.  **The Adapter Layer:** Code that translates MCP `CallToolRequest` -> `engines` `RequestContext` + Service Call.
3.  **The Workbench UI Backend:** API to support the Workbench UI (ingest, define, save draft, publish).
4.  **The "Sandbox":** A way to "dry run" a connector against the real engine without full deployment.

## Existing "Almost" Solutions

*   `engines/chat/service/server.py` mounts routers. This is the pattern to copy for the MCP Gateway.
*   `engines/common/identity.py:RequestContextBuilder` is the key to solving the "Auth Translation" gap.
*   `engines/registry/service.py` is the key to solving the "Tool Discovery" gap.

## Strategic Placement

*   **Location:** `engines/mcp_gateway/` (New Directory).
*   **Type:** Sibling FastAPI app (like `admin_api` or `public_api`).
*   **Dependency:** Depends on `engines.common`, `engines.registry`, `engines.firearms`, `engines.routing`.
*   **Why here?** It allows direct, in-process calls to `FirearmsService.check_access` and `RegistryService.get_components` without going back out over HTTP, ensuring strictly enforced internal policy.
