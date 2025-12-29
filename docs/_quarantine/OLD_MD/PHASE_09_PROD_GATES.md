# PHASE 9 — Production Hardening Checklist

> [!NOTE]
> **DONE**: Implemented `RateLimitService` and `QuotaService` stubs. Wired `KillSwitchService` and `RateLimitService` into all 8 Nexus routes (`raw`, `atoms`, `cards`, `index`, `packs`, `settings`, `runs`, `memory`). Verified enforcement via `test_prod_gates.py`.

Goal:
- SaaS-grade operational hardening: limits, quotas, kill-switch integration, monitoring, deletion flows.

In-scope (engines only):
- Rate limits on heavy routes (upload presign, search/index, pack creation); quotas per tenant (storage bytes, indexing ops).
- Kill-switch integration: provider/action disablement blocks indexing/LLM calls where applicable; surface clear errors.
- Monitoring hooks: success/failure metrics for storage/index/search/pack routes; alerting-ready.
- Documentation: operational env vars, migration steps, purge/delete tenant data (GDPR deletion flow) referencing PII contract.
- DatasetEvents for quota hits, deletions, kill-switch triggers with tenant/env/user/trace.

Out-of-scope:
- Changing business logic of KPI/Temperature or adding orchestration rules.
- Implementing external monitoring systems; only hooks/contracts defined.

Affected engine modules:
- `engines/nexus/*` routes/services, `engines/kill_switch`, `engines/logging/events`, `engines/config`, `engines/identity/auth`.

Runtime guarantees added:
- Quota/rate checks are tenant/env scoped and enforced; errors are deterministic and logged.
- Kill-switch flags block relevant actions; no silent bypass.
- Deletion/purge flows remove tenant data from storage/index/logs where applicable and emit audit trails.

What coding agents will implement later:
- Add limiters/quotas, hook kill-switch checks, emit metrics/events, document ops steps; add tests for quota/kill-switch enforcement and deletion auditing.

How we know it’s production-ready:
- Quota exceed paths return clean errors and audit logs; kill-switch blocks observed in tests.
- Deletion flow tested to remove tenant data and emit DatasetEvents; monitoring hooks validated in smoke tests.
