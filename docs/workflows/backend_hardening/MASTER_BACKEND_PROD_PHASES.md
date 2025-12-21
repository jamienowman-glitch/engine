# MASTER_BACKEND_PROD_PHASES

Ordering (must execute in order):
1. PHASE_01_CHAT_RAILS_PROD.md
2. PHASE_02_NEXUS_CONTROL_PLANE_PROD.md
3. PHASE_03_RAW_STORAGE_PRESIGN_REGISTER_PROD.md
4. PHASE_04_AUDIT_LOGGING_TRACE_PROD.md
5. PHASE_05_GATECHAIN_EXTERNAL_MUTATIONS_PROD.md
6. PHASE_06_STORAGE_PREFIX_ENFORCEMENT_PROD.md
7. PHASE_07_SMALL_LEAKS_CLEANUP_PROD.md

Dependencies:
- Phase 1 must land before any GateChain/workloads because WS/SSE isolation is currently weak (`engines/chat/service/ws_transport.py`, `engines/chat/service/sse_transport.py`).
- Phase 2 builds auth/membership on Nexus routes so later gate/storage fixes operate on authenticated tenants.
- Phase 3 fixes raw storage API surface; Phase 4 depends on it for audit emit correctness.
- Phase 4 turns audit pipeline on; Phase 5 GateChain assumes audit emits are reliable.
- Phase 6 enforces tenant/env prefixes after GateChain is ready.
- Phase 7 closes remaining leaks (temperature config auth, chat pipeline tenant defaults, etc.).

Shared modules (integration-coordinated): `engines/common/identity.py`, `engines/identity/auth.py`, `engines/chat/service/server.py`, `engines/logging/audit.py`, `engines/logging/events/engine.py`, `engines/realtime/contracts.py`, `engines/kill_switch/service.py`, `engines/strategy_lock/service.py`. If touched, mark PR as integration-required and re-run full test set.
