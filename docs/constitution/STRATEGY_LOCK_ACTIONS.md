# Strategy Lock Action Classification

Canonical classification for when Strategy Lock (and optional 3-Wise/HITL) must be invoked. Applies across orchestrators, planners, and tools.

## Require Strategy Lock (+ optional 3-Wise)
- Outbound sends: real email dispatch, social post/publish/update, push notifications.
- Spend/financial: ad spend/budget edits, bidding changes, billing/pricing changes, purchase/refund issuance.
- Code/infra: code writes, migrations, deploys, config/toggles that affect prod behaviour, DNS/infra changes.
- Credentials/identity: connector auth/permissions changes, key rotations, tenant/user role escalations.
- Data destruction/high-risk data writes: destructive updates/deletes to datasets, PII writes outside corridors.
- Temperature planning: **planning job only** when proposing weight increases on risk-tolerance/sales-emphasis axes.
- Any action flagged as firearms high/critical by registry/tenant constitution.

## Do NOT require Strategy Lock
- Temperature measurements (runtime path): read plan + measure only.
- Internal reads: analytics/BI/log reads without side effects.
- Drafting: ideas/briefs/notes/snippets saved to blackboards/Nexus without delivery/publish.
- Routine content edits inside allowed corridors (non-outbound, non-destructive) when corridor and firearms allow.
- Logging/DatasetEvent emissions and corridor reads.

## Guardrail notes
- Strategy Lock may request 3-Wise for high/critical risk or when increasing risk_tolerance; HITL may still be required per firearms/tenant policy.
- Keyword policy remains pluggable; this list is canonical for OS/enterprise wiring and should be mirrored in routing/agents.
