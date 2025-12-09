# CAIDENCE Engine Wiring (repo-side)

- Chat transports (HTTP/WS/SSE) call `engines.chat.pipeline.process_message`, which:
  - Writes chat snippets to Nexus via the configured backend (NEXUS_BACKEND=firestore).
  - Logs DatasetEvents via `engines.logging.events.engine` (PII-stripped).
  - Emits a stub orchestration response (non-echo) pending ADK/LLM delegate wiring.
- Nexus backend selection lives in `engines/nexus/backends/__init__.py`; Firestore backend uses tenant-scoped collections: `nexus_snippets_{TENANT_ID}`, `nexus_events_{TENANT_ID}`.
- Media ingest engines call `engines.storage.gcs_client.GcsClient` when `RAW_BUCKET`/`DATASETS_BUCKET` are set, uploading to tenant-scoped paths.
- Guardrails: PII strip runs before logging; Strategy Lock / 3-Wise return policy-aware decisions (ALLOW/BLOCK/HITL markers).
- Temperature engine computes bands from weighted KPIs and exposes update hooks for external agents to adjust weights.
- Temperature plans: engines load `TemperatureWeightsPlan` from Nexus (Firestore) via service helper before computing band; measurements are logged as DatasetEvents.
- SEO/FUME primitives are present in `DatasetEvent` and `engines/seo/helpers.py`; connectors can map events to GA4/Meta/Snap/TikTok.
