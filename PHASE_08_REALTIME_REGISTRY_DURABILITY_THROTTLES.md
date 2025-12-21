# PHASE_08_REALTIME_REGISTRY_DURABILITY_THROTTLES

## Goal
Replace the in-memory thread/canvas registry with a durable backing (Firestore or similar) and add per-tenant throttles so streaming isolation scales to 1M tenants while still honoring replay/resume requirements.

## In-scope / Out-of-scope
- **In-scope:** `engines/realtime/isolation.py`, `engines/realtime/tests/*`, `engines/nexus/hardening/rate_limit.py`, `engines/nexus/hardening/tests/*`, any new helper modules for durable registry persistence.
- **Out-of-scope:** Media layer registries, FE presence components.

## Required invariants
1. Registry operations (`register_thread`, `register_canvas`, `get_*_tenant`) must optionally delegate to Firestore (or another durable store) controlled by config; the in-memory fallback remains for tests.
2. Rate limit service must track per-tenant usage (already the case) and the throttle configuration should support resetting windows even after process restarts when backed by persistent store.
3. Streaming isolation continues to call `verify_thread_access` and `verify_canvas_access`, returning 404 if the resource is not registered or owned by another tenant.

## Allowed modules to change
- `engines/realtime/isolation.py`
- `engines/realtime/tests/*`
- `engines/nexus/hardening/rate_limit.py`
- `engines/nexus/hardening/tests/*`
- Supporting config/helpers under `engines/config` only if required (limited touches).

## Step-by-step tasks
1. Abstract the registry behind an interface that allows swapping in a Firestore-backed implementation (`RealtimeRegistry`), defaulting to the current in-memory one; new implementation should store thread/canvas ownership documents keyed by resource ID.
2. Update unit tests to mock the durable store and cover scenarios where Firestore data is stale (thread moved to new tenant) or missing, ensuring `verify_*_access` raises 404.
3. Enhance `engines/nexus/hardening/rate_limit.py` to accept an optional persistent backend (e.g., Firestore document storing counters) to avoid resetting counters on restart; tests should verify throttles stay tenant-isolated even if the process restarts between requests.
4. Document in this phase the operations needed to seed registry entries (e.g., from Nexus create flows) so FE/FE proxies know how to register threads/canvases.
5. Add a guard in streaming transports (from Phase 1) that logs when `registry.get_*_tenant` returns `None`, ensuring detection of missing entries.

## Tests
- `pytest engines/realtime/tests/test_isolation.py::test_durable_registry_blocks_wrong_tenant`
- `pytest engines/nexus/hardening/tests/test_rate_limit.py::test_throttle_survives_restart`

## Acceptance criteria
- Durable registry operations succeed when configured, and isolation logic keeps denying access to unregistered threads/canvases.
- RateLimit service preserves tenant quotas across restarts when durable backend enabled, and tests cover tenant isolation.
- The plan to seed registry entries is documented (since writes require pre-registration).

## Stop conditions
- Stop if Firestore client wiring requires touching environment/config modules beyond the allowed scope.
- Stop if durable backend readiness depends on network access to Firestore without credentials; escalate for infra support.

## Do-not-touch list
- `engines/chat/service/*` (unless debugging cross-phase gating).
- `engines/config/runtime_config.py` (unless strictly required for Firestore client, which should be deferred).

## Mini execution guardrails
- If any required change touches files outside the allowed modules, STOP and file a blocking issue before continuing.
