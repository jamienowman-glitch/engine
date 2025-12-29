# TOOL REGISTRY GROUNDWORK (PLANNING)

Unified tool language for agents/clusters. Planning-only; no runtime registry yet.

## Tool Descriptor schema (conceptual)
Fields:
- `tool_id`: stable ID (`provider.scope.action` or `ns.<domain>.<action>`).
- `kind`: `external_mcp` | `internal_engine` | `http_api` | `local_helper`.
- `description`: short human-readable text; no hidden prompts.
- `input_schema` / `output_schema`: JSON Schema refs; align with MCP signatures where applicable.
- `firearms_class`: links to Firearms Registry (null if not risky).
- `cost_hint`: `{ latency_ms, tokens, dollar }` rough estimates for orchestration scoring.
- `allowed_clusters` / `allowed_gangs`: clusters/gangs permitted to call; empty means none.
- `tenant_scope` / `env_scope`: optional allowlist.
- `cooldown_s` and optional `rate_limit` (`per_minute`, `burst`) for pacing.
- `transport`: config specific to `kind` (see below).

```json
{
  "tool_id": "shopify.list_products",
  "kind": "external_mcp | internal_engine | http_api | local_helper",
  "description": "List products from Shopify",
  "input_schema": { "$ref": "..." },
  "output_schema": { "$ref": "..." },
  "firearms_class": "outbound_web | spend_budget | ... | null",
  "cost_hint": { "latency_ms": 500, "tokens": 0, "dollar": "low" },
  "allowed_clusters": ["catalog_cluster"],
  "allowed_gangs": ["ecom_gang"],
  "tenant_scope": ["t_northstar-dev"],
  "cooldown_s": 0,
  "rate_limit": { "per_minute": 60, "burst": 10 },
  "transport": { "mcp_server": "shopify_server", "mcp_tool": "list_products" }
}
```

## Kinds
- `external_mcp`: MCP servers (e.g., connectors service); transport carries `mcp_server`, `mcp_tool`, auth hints.
- `internal_engine`: direct engine/Cloud Run entrypoint; transport carries `run_url`, `method`, `auth_mode` (service account, signed URL).
- `http_api`: existing HTTP service callable via HTTP; transport carries `method`, `url`, `headers`, `auth`.
- `local_helper`: in-process helper; transport carries `module`, `function`, version.

Agents see only the descriptor; a router resolves how to call based on `kind`.

## Firearms linkage
- `firearms_class` links to Firearms Registry; null if not risky.
- If firearms licence not granted for tenant, tool is hidden/blocked.
- Strategy Lock/3-Wise invoked per firearms/tenant rules; HITL if required.

## Exposure to clusters and capabilities
- Cluster/agent cards list `tools: [tool_id, ...]`; router enforces intersection of descriptor `allowed_clusters/gangs` with cluster ID/gang.
- Capabilities (CLUSTER_CAPABILITIES) still gate what paths the cluster can write/read; Tool Registry only controls callable tools.
- Tenant/env scopes apply before exposure; no descriptor → no call.
- Cooldowns/rate limits apply per tool + tenant; rails enforce before invoking transport.

## MCP fit (design only)
- `external_mcp` descriptors map to MCP servers; input/output schemas align with MCP tool signatures.
- Router chooses MCP vs internal vs HTTP based on `kind`; agents remain agnostic.
- MCP tools must also carry firearms/capability metadata so orchestrators can reason before calling.

## Outputs and manifest alignment
- Tools return structured outputs (snippets, events, patches). Manifest/token graph remains the target for content/tokens.
- Orchestrators apply outputs under capability rules; tools themselves never bypass manifest/token graph or write to Nexus directly unless defined in the descriptor.

## Non-goals (this pass)
- No storage layer or API for the registry.
- No auth wiring; contracts only.
