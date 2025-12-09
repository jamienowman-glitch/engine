# CLUSTER CAPABILITIES & SCOPED PATCHING

Contracts for how clusters/agents are scoped to specific manifest paths and operations. This is design-only; enforcement/auth wiring is out of scope for this pass.

## Capability descriptor (schema)
- `cluster_id`: stable ID for the cluster (e.g., `typography_cluster`).
- `label`: human-friendly name.
- `clique`: capability family (e.g., `typography`, `layout`, `copy`, `colour`).
- `gang`: optional grouping for scheduling/ownership (e.g., `web_typography_gang`).
- `surface_scope` / `app_code` / `tenant_scope`: optional filters for where this descriptor applies.
- `allowed_reads`: path globs the cluster may read to build context.
- `allowed_writes`: path globs the cluster may mutate.
- `allowed_ops`: subset of patch ops (`set`, `delete`, `merge`).
- `notes`: optional free-text rationale or constraints.

```json
{
  "cluster_id": "typography_cluster",
  "label": "Typography Cluster",
  "clique": "typography",
  "gang": "web_typography_gang",
  "allowed_reads": ["content_slots.*", "tokens.typography.*"],
  "allowed_writes": ["tokens.typography.*"],
  "allowed_ops": ["set", "merge"]
}
```

Typical examples:
- Layout cluster: reads `content_slots.*`, `tokens.layout.*`; writes `tokens.layout.*`; ops `set|merge`.
- Copywriting cluster: reads `tokens.typography.*`, `tokens.layout.*`; writes `content_slots.headline.*`, `content_slots.body.*`; ops `set`.
- Behaviour/animation cluster: reads `components.*`, `tokens.layout.*`; writes `tokens.behaviour.*`; ops `set|merge`.

## Path globs and families
- Paths use dot-separated segments from the manifest contract: `components.<id>`, `content_slots.<component>.<slot>`, `tokens.<domain>.<component>.<field>`, `metadata.<field>`.
- `*` matches a single segment; globs are evaluated per segment (e.g., `tokens.typography.*` matches `tokens.typography.hero_headline` but not `tokens.layout.hero_headline`).
- Allowed domains mirror manifest tokens: `typography`, `layout`, `colour`, `behaviour` (extendable with the same shape).
- Capabilities must not grant cross-family writes (e.g., copy clusters should not write `tokens.*`; typography clusters should not write `content_slots.*` unless explicitly allowed).

## Patch contract (design level)
```json
{
  "manifest_id": "m_123",
  "changes": [
    { "path": "tokens.typography.hero_headline.tracking", "op": "set", "value": 150 },
    { "path": "content_slots.hero_headline.text", "op": "set", "value": "New headline" }
  ],
  "actor": { "actor_type": "agent", "cluster_id": "typography_cluster", "agent_id": "typography_agent_v1" },
  "request_id": "req_123",
  "timestamp": "ISO8601"
}
```

Allowed ops:
- `set`: replace the value at the path.
- `delete`: remove the path (e.g., delete a token field or component entry).
- `merge`: shallow merge into an object (for token dictionaries), never for content primitives.

Validation rules (deferred to enforcement layer):
- Each change path must match an `allowed_writes` glob for the actor’s cluster; reads for context are limited to `allowed_reads`.
- Each op must be in `allowed_ops` and compatible with the path family (no `merge` on scalar slots, no `delete` on immutable metadata).
- Patches cannot touch immutable root fields (`manifest_id`, `tenant_id`, `app_code`, `surface`, `env`).
- Removing a component requires companion removals of its content slots/tokens in the same patch batch.
- Reject the entire patch if any change violates capabilities or shape rules; there is no “regenerate view” or bulk rewrite operation.

## Origin & metadata
- Every patch carries `origin` (`human`|`agent`), `cluster_id`, `agent_id` (or `human_id`), and optional `request_id`/`prompt_hash`/reason.
- Human edits may be tagged as locks/high-priority hints; agents may stage drafts in blackboards before apply.
- Downstream logs/Nexus records must persist the actor metadata for audit and future Strategy Lock checks.

## Non-goals (this doc)
- No ACL/auth plumbing, no transport, no storage decisions.
- No conflict-resolution mechanics; only the contract and intent are defined here.
