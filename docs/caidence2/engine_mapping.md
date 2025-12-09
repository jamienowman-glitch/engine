# CAIDENCE² ENGINE MAPPING (PHASE 1)

Mapping of existing engines to CAIDENCE² roles. Status codes: Ready | Needs IO Tweak | Needs Adapter.

| Role | Candidate engine(s) | Status | Notes |
| --- | --- | --- | --- |
| Chat surface / orchestrator | `engines/chat` (HTTP/SSE), can bridge WS later | Needs IO Tweak | Verify `app_id='caidence2'` handling, tenant validation, and streaming path; ensure prompts come from ADK cards only. |
| Nexus read/write | `engines/nexus` (Firestore backing) | Needs Adapter | Confirm namespaces (`style_nexus`, `content_nexus`, `events`) and card-driven configs; add adapter if ADK paths differ. |
| PII strip / data hygiene | `engines/text/clean_asr_punct_case`, `engines/audio/preprocess_basic_clean` | Needs Adapter | Likely sufficient for basics; need CAIDENCE²-specific PII policies and redaction coverage for chat/logging. |
| Guardrails (Strategy Lock + 3-Wise) | Strategy Lock policy + logging hooks (no dedicated engine folder) | Needs Adapter | Integrate to CAIDENCE² corridors/firearms; ensure action classification wired for chat/actions; may require new adapter service. |
| Temperature / KPI band engine | Temperature engine (per `TEMPERATURE_PLANS`) | Needs IO Tweak | Plan schemas ready; ensure CAIDENCE² plans exist and Firestore collections/tenants configured; add Nexus fetch helper if absent. |
| SEO/UTM & logging | `engines/seo`, `engines/logging` | Needs Adapter | Confirm dataset event shapes align to CAIDENCE² KPIs/UTM; likely requires adapter for per-tenant destinations and GA/ads wiring. |

Gaps/TODOs:
- Validate real production configs/secrets for CAIDENCE² before enabling (plan is production only).
- Confirm card-driven manifests/routes from ADK are present; add thin adapters where IO differs.
- Align Strategy Lock/3-Wise invocation for outbound/publish actions and temperature planning path.
