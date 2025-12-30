# Phase 0→2 Gate2 Checklist (Mode-only, No-InMemory)

- [x] Memory Durable (PR #4 / commit f2f17f4) — tenant/mode/project scoped storage; tests/test_memory_persistence.py.
- [x] Stream Replay Durable (PR #6) — SSE/WS resume from durable timeline; tests/logs/test_stream_replay.py.
- [ ] AuditChain (hash chaining + storage_class=audit) — DoD: prev_hash/hash recorded per event; tests/logs/test_audit_hash_chain.py.
- [x] Cost kill-switch + /ops/status + Azure env stubs (PR #5) — usage events carry run/step/model/tool and Azure config registered.
- [x] Vector-ish knowledge ingest + retrieval (PR #7 / commit 78b629e) — mode headers, full envelope, PII pre-call, durable logger.
