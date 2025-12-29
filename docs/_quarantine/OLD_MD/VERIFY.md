# Realtime Hardening Verification Checklist (Bossman)

**Objective:** Verify compliance with `REALTIME_SPEC_V1` (Phases 1-3).
**Status:** Ready for Review

## 1. Interface Contracts
- [x] **Canonical Event:** `StreamEvent` exists in `engines/realtime/contracts.py` and is strict.
- [x] **Legacy Check:** All chat messages are adapted via `from_legacy_message`.

## 2. Security & Isolation
- [x] **Route Validation:** `validate_routing` exists and is used.
- [x] **Resource Ownership:** `verify_thread_access` and `verify_canvas_access` enforce `tenant_id` ownership (registry stubbed for deterministic testing).
- [x] **Tests:** `test_isolation.py` confirms 403 Forbidden on cross-tenant access.

## 3. Transport Rails
- [x] **WebSockets:** `/ws/chat` accepts auth token, validates tenant, handles gestures (passthrough), emits presence.
- [x] **SSE:** `/sse/canvas` validates tenant, emits commits.

## 4. Commands & Conflict Resolution
- [x] **Optimistic Concurrency:** `apply_command` strictly checks `base_rev`.
- [x] **Idempotency:** Replaying same key returns success but no side-effect.
- [x] **Endpoint:** `POST /commands` is live (stubbed persistence).

## 5. Storage
- [x] **Pathing:** GCS writes strictly to `tenants/{tenant_id}/{env}/...`.
- [x] **Tests:** `test_paths.py` confirms enforcement.

## 6. Known Gaps
*   **Stubs:** `CommandRepository` and `run_registry` are in-memory. Require Nexus/Postgres wiring in future phase.
*   **Legacy Bus:** Event Bus is still `InMemoryBus`. Works for single-node.
