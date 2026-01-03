# Phase 0.6 — Attribution/Analytics Parallel Plan

## Two-worker split
- Worker A (Attribution + Analytics backend)
  1) AttributionContractV1 models/routes/service via tabular_store (routing). 
  2) tag_link endpoint using contract. 
  3) Analytics model expansion (scope + platform), routing-backed storage, query endpoints, GateChain status persistence. 
  Commit order: A1 contract, A2 tag_link, A3 analytics ingest/query + gate handling.

- Worker B (Fonts/Per-letter + SEO scope)
  1) PerLetterStyleV1 token + renderer support. 
  2) Multi-font ingestion/registry via object_store/tabular_store. 
  3) SEO scoping correction (mode/project/app/surface) with routing-backed repo.
  Commit order: B1 per-letter, B2 font ingestion, B3 SEO scope/persistence.

Dependency: Independent if routing registry exists; ensure shared typography files not clobbered.

## Three-worker split
- Worker A: Attribution contract + tag_link + routing-backed tabular_store.
- Worker B: Analytics ingest/query expansion + routing-backed analytics_store/metrics_store + GateChain status persistence.
- Worker C: Per-letter renderer + multi-font ingestion + SEO scope correction.

Ordering:
1) A/B can proceed in parallel once routing registry present.
2) C can proceed independently; coordinate if shared font registry touched.

## Merge rules
- Land attribution/analytics routing changes before UI or connectors rely on them.
- Keep font registry changes isolated; add fixtures/tests per font.
- Ensure gate/status behavior is covered by tests before merging analytics changes.
