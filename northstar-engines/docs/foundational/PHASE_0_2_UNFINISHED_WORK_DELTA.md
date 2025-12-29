# Phase 0→2 Unfinished Work Delta (Mode + No-InMemory, facts only)

- RequestContext lacks mode and still uses X-Env; body/query fallbacks allow legacy env values (engines/common/identity.py:22-151). Blocks mode requirement.
- Event schemas missing mode/project/app/run/step/schema_version/severity/storage_class (engines/dataset/events/schemas.py:9-32; engines/realtime/contracts.py:74-165). Blocks canonical envelope.
- In-memory/no-op paths remain:
  - Memory repo defaults to InMemory (engines/memory/repository.py:104-111).
  - Nexus memory uses in-memory dict `_GLOBAL_MEMORY` (engines/nexus/memory/service.py:16-72).
  - Chat bus replay uses in-memory/Redis, no durable timeline (engines/chat/service/transport_layer.py:65-121).
  - Vector explorer event logger defaults to no-op (engines/nexus/vector_explorer/service.py:167-175; ingest_service.py:32-47).
  - Budget repo defaults to InMemory (engines/budget/repository.py:175-182).
- PII pre-call redaction missing for embeddings/LLM: chat llm_client sends raw prompts (engines/chat/service/llm_client.py:27-50); vector explorer query/ingest send raw text_content (engines/nexus/vector_explorer/service.py:107-135; ingest_service.py:168-188).
- SSE/WS replay not durable; resumes from bus only (sse_transport.py:23-68; ws_transport.py:136-205; transport_layer.py:65-121). Blocks replay contract.
- Audit lacks hash chaining/append-only sink; emit_audit_event uses DatasetEvent only (engines/logging/audit.py:18-53; ingest_service.py:160-165).
- Mode concept absent everywhere; only env supported. Blocks mode adoption across transports/logging/routing.
- UI/client headers not enforced for mode/tenant/project; transports only check tenant; project/app not enforced on SSE/WS (sse_transport.py:44-58; ws_transport.py:137-160).
