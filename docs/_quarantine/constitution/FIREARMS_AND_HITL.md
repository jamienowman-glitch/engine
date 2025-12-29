# FIREARMS & HITL GROUNDWORK (PLANNING)

Planning-only contract for firearms licensing, tenant constitutions, and interaction with Strategy Lock / 3-Wise. No runtime wiring in this pass.

## Conceptual layers
- **OS constitution**: global defaults and firearms classes.
- **Tenant constitution**: per-tenant licensing/requirements for firearms classes.
- **Tool/agent metadata**: each tool/agent declares which firearms classes it can exercise.
- **Effective clearance**: computed intersection of the above + environment (dev/stage/prod) to decide if an action can run and what gates apply.

## Firearms classes (extensible)
- outbound_email: send emails to customers/prospects.
- outbound_social: post/publish/edit on social platforms.
- outbound_web: publish/update live web/app content.
- spend_budget: modify ad/campaign spend or bidding.
- connector_auth_change: rotate/regenerate connector credentials.
- destructive_data: delete/update high-risk data.
- dns_or_infra_change: mutate DNS/infra knobs.
- Treat classes as capability labels, not marketing tags; more can be added.

## Firearms Registry schema (conceptual)
```json
{
  "firearms_id": "outbound_email",
  "description": "Send email to customers/prospects",
  "risk_level": "high",
  "requires_hitl": true,
  "default_cooldown_s": 0,
  "default_strategy_lock": true,
  "notes": "Only permitted for licensed tenants; Strategy Lock + 3-Wise required."
}
```
- Fields: `firearms_id`, `description`, `risk_level` (low|medium|high|critical), `requires_hitl`, optional `default_cooldown_s`, `default_strategy_lock`, `notes`.
- Referenced by: tools, cluster/agent cards, tenant constitutions.

## Tenant constitution switches (design only)
- Per `firearms_id`, tenants store:
  - `licence_granted: bool`
  - `requires_hitl_override: bool|null` (null = use registry default)
  - `cooldown_s_override: int|null`
  - `notes`, `last_reviewed_at`
- Example:
```json
{
  "firearms_id": "outbound_email",
  "licence_granted": true,
  "requires_hitl_override": true,
  "cooldown_s_override": 3600,
  "notes": "Only for marketing; no transactional sends."
}
```
- Constitutions are read by orchestrators/routers before exposing tools to clusters; unlicensed firearms are hidden.

## Tool/agent metadata
- Tools/agents declare `firearms: [<firearms_id>]` and optional `requires_hitl: bool|null` (null = use registry/tenant effective value).
- Tool Registry links firearms_id to cluster capabilities; routers must not route a firearms-tagged tool to a cluster lacking the corresponding licence.
- Agents must not self-assign firearms classes; they consume Tool Registry entries with explicit metadata.

## Strategy Lock / 3-Wise / HITL interaction
1) Capability exposure: if `licence_granted` is false, firearms-tagged tools are not surfaced to orchestrators/clusters.
2) Strategy Lock: if `default_strategy_lock` (or tenant override) is true, Strategy Lock must approve before execution; high/critical risk implies 3-Wise review.
3) HITL: if effective `requires_hitl` is true, rails create a HITL task; auto-action is blocked until approval; approvals logged with `request_id`.
4) Cooldown/pacing: rails enforce `default_cooldown_s` or tenant override between approvals/executions of the same firearms class per tenant.
5) Audit: every approval/denial emits DatasetEvents carrying `firearms_id`, `tenant_id`, `actor_id`, `cluster_id`, and decision.

## Fit with existing guardrails
- Strategy Lock action classification stays the policy brain; firearms class is a trigger to involve it.
- 3-Wise provides risk triage/logging; firearms metadata provides the “this can do damage” flag.
- PII strip/Temperature still apply where relevant; firearms is orthogonal but coexists with those guardrails.

## Non-goals (this pass)
- No code, no persistence; schema/contract only.
- No UI for licences; only the shapes and interaction rules.
