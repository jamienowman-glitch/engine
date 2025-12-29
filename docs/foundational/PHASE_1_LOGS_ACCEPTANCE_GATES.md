# Phase 1 Logs — Acceptance Gates (runnable checks)

1. **Event contract gate**  
   - Check: canonical envelope validates required fields + schema_version + severity.  
   - Verify: `python -m pytest tests/logs/test_event_contract.py`.

2. **Context gate**  
   - Check: emitted events from mounted routers include tenant/env/project/surface/app/user/request_id/trace_id/run_id.  
   - Verify: `python -m pytest tests/logs/test_correlation_propagation.py`.

3. **PII gate**  
   - Check: redaction applied before tool/model/LLM calls and before persistence; encrypted payload hook optional.  
   - Verify: `python -m pytest tests/logs/test_pii_gate.py`.

4. **Audit gate**  
   - Check: audit sink enforces append-only with hash chaining; sample run shows prev_hash/hash continuity.  
   - Verify: `python -m pytest tests/logs/test_audit_hash_chain.py`.

5. **Streaming gate**  
   - Check: SSE/WS selective streams replay from durable store with stable ordering; resume cursor works.  
   - Verify: `python -m pytest tests/logs/test_stream_replay.py`.

6. **Usage gate**  
   - Check: usage_recorded events carry token/cost/model/tool/run/step and are queryable by tenant/run.  
   - Verify: `python -m pytest tests/logs/test_usage_events.py`.

7. **Retention gate**  
   - Check: retention/export/delete commands honor per-tenant policy and emit audit trail of deletions.  
   - Verify: `python -m pytest tests/logs/test_retention_export.py`.

8. **Structured dev logs gate**  
   - Check: Python logger emits JSON with request_id/trace_id/tenant/project and links to event_id on exceptions.  
   - Verify: `python -m pytest tests/logs/test_structured_logging.py`.
