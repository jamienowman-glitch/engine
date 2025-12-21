# Canvas Backend Master Plan (Docs-Only)

Phases focus on backend rails, tenancy, persistence, and streaming needed for FE canvas + graft. No prompts/orchestration/FE code.

## Phase List
- PHASE 00 — Backend truth scan + contract freeze (BACKEND_TRUTH.md)
- PHASE 01 — Tenancy baseline: Tenant-0 + Tenant-1 and feature flag surface
- PHASE 02 — Realtime rails foundation (SSE + WS)
- PHASE 03 — Command + revision apply (minimum viable, deterministic)
- PHASE 04 — Artifact store + Nexus persistence (preview/replay/audit)
- PHASE 05 — Graft support (live gestures vs auto-mode replay)
- PHASE 06 — Minimal audit endpoints (scaffolding)

Each phase file defines: goal, scope, allowed modules, explicit steps, tests, stop conditions, and do-not-touch lists.

## Backend Truth Summary (current state)
| Area | Status | Notes |
| --- | --- | --- |
| RequestContext / tenancy | ⚠️ | `engines/common/identity.py` exists; many routes use it, but chat/video/media routes do not enforce it. |
| Auth | ⚠️ | HS256 + optional Cognito (`engines/identity/auth.py`, `routes_auth.py`); only some routers depend on it. |
| Event logging | ✅ | DatasetEvent pipeline (`engines/logging/events/engine.py`), audit helper (`engines/logging/event_log.py`). |
| Nexus write paths | ⚠️ | `engines/nexus/backends/*`; used by chat pipeline; some Nexus routes incomplete/broken. |
| Streaming (WS/SSE) | ⚠️ | Chat WS/SSE stubs (`engines/chat/service/ws_transport.py`, `sse_transport.py`), no auth/tenant, no resume. |
| Command/revision primitives | ❌ | No revision head/base_rev pattern anywhere. |
| Artifact storage | ⚠️ | `engines/media_v2` defaults to S3 via `RAW_BUCKET` (`boto3`) with local fallback; Firestore/memory metadata; raw_storage S3 presign/register exists but routes need fixes and auth. |

## FE Blocking Items
- Tenancy enforcement gaps on streaming and media/timeline/render routes.
- No revision/logging primitives for canvas edits.
- No SSE channel for canvas commits/gestures; WS lacks presence/heartbeat.
- No Tenant-0/feature-flag surface; Tenant-1 bootstrap not codified.
- Nexus/raw_storage routes have broken dependencies; cannot persist drafts reliably with scoping.

## Safe to Start FE Canvas Build When…
- Tenant-0/1 exist with auth + feature toggles for rails/gesture logging.
- WS (chat/tool/presence) and SSE (canvas commits/artifact notifications) enforce routing keys + RequestContext + reconnect semantics.
- Command endpoint returns deterministic rev head or REV_MISMATCH with recovery payload.
- Preview/replay/audit artifacts persist binaries to storage and metadata to Nexus with lineage.
- Gesture stream isolated per tenant/canvas; auto-mode generates keyframed replay + audit log.
