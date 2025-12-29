# Phase 0→2 Status Update (Mode-only, No-InMemory)

- Gate0 Storage: GCS PASS (gs://northstar-os-dev-northstar-raw, key tenants/t_system/lab/media_v2/smoke/<ts>.txt); S3 supported but blocked by AccessDenied on PutObject to bucket northstar-dev-boy for user northstar-dev.
- Gate1 Mode/Context: DONE (ModeCTX implemented).
- Gate1 Event Envelope: DONE (contract enforcement implemented) — integration merge needed with ModeCTX.
- Gate1 Integration Merge required: ModeCTX + Envelope.
- Gate1 Next lanes: No-InMemory/No-Noop, then PII pre-call.
- Agents: AgentsRequestContext + audit correlation alignment DONE.
- UI: transport header injection + mode adoption DONE; WS auth still TODO choke-point.
