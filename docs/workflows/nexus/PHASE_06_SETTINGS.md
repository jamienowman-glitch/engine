# PHASE 6 — Settings & Control Screens APIs

> [!NOTE]
> **DONE**: Implemented `SettingsService` as a facade for typed `Card` retrieval. Routes for surface/apps/connectors added.

Goal:
- Serve tenant-configurable settings as data (cards) with Strategy Lock/role gating, no hardcoded behaviors in engines.

In-scope (engines only):
- Treat settings as cards (surface settings, app rituals, connector contributions) using Phase 3 card format.
- Routes: `GET /settings/surface`, `GET /settings/apps`, `GET /settings/connectors` returning cards + parsed YAML for tenant/env.
- Writes of strategic settings gated by Strategy Lock and owner/admin roles (via card creation/revision endpoints).
- DatasetEvents for reads/writes with tenant/env/user/trace; pii_flags/train_ok enforced.

Out-of-scope:
- UI rendering logic, orchestration rules, or behavior tied to settings content.
- Changing KPI/Temperature meanings; only exposing configs as data.

Affected engine modules:
- `engines/nexus/cards`, `engines/nexus/index` (for filtered reads), `engines/strategy_lock`, `engines/identity/auth`, `engines/logging/events`.

Runtime guarantees added:
- Settings reads/writes tenant/env scoped; strategic edits gated; missing auth/context fails closed.
- Returned payloads contain data only (no prompts/logic); parsed YAML available for UI consumption.

What coding agents will implement later:
- Implement filtered card retrieval for settings types; add role + Strategy Lock enforcement; add tests for gating and tenant isolation.
- Add read-model helpers for dashboard summaries.

How we know it’s production-ready:
- Tests show owner/admin-only edits with Strategy Lock required; members can read scoped settings.
- UI can fetch settings data via APIs; cross-tenant reads blocked; DatasetEvents emitted.
