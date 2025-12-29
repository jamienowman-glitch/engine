1. Goal  
Replace stub detectors with real, deterministic backends and artifact contracts for regions, visual_meta, captions, and anonymise; ensure render/anonymise consume them for CapCut-lite editing.

North star + Definition of Done  
- North star slice: CapCut-class detection/anonymise/captions for 2–3 minute face-to-camera and b-roll clips on CPU/GPU, with versioned artifacts reused by render.  
- Definition of Done:  
  - video_regions/video_visual_meta/video_captions/video_anonymise use non-stub backends (CPU default, GPU optional) with deterministic outputs and versioned meta.  
  - media_v2 artifacts for `video_region_summary`, `visual_meta`, `asr_transcript` are registered with validated schemas; render/anonymise consume them end-to-end.  
  - Tests cover success/failure on at least two fixtures (face clip + b-roll), plus stub fallbacks and missing-dep paths.  
  - A worker can POST /video/regions → get artifacts → POST /video/anonymise → POST /video/render to produce blurred/captioned output without manual patching.

2. Scope (In / Out)  
- In: video_regions, video_visual_meta, video_captions, video_anonymise, render consumption, media_v2 artifact kinds/meta, env-based backend selection.  
- Out: auth/tenant/spine/orchestration, UI, budgets/locks, CDN, new product surfaces.

3. Modules to touch  
- engines/video_regions/service.py  
- engines/video_regions/backend.py  
- engines/video_regions/routes.py  
- engines/video_regions/tests/test_video_regions_service.py  
- engines/video_regions/tests/test_video_regions_routes.py  
- engines/video_regions/tests/test_real_backend.py  
- engines/video_visual_meta/service.py  
- engines/video_visual_meta/backend.py  
- engines/video_visual_meta/routes.py  
- engines/video_visual_meta/tests/test_visual_meta_endpoints.py  
- engines/video_captions/service.py  
- engines/video_captions/backend.py  
- engines/video_captions/routes.py  
- engines/video_captions/tests/test_captions_gen.py  
- engines/video_anonymise/service.py  
- engines/video_anonymise/routes.py  
- engines/video_anonymise/tests/test_service.py  
- engines/video_render/service.py (only region/caption/visual-meta consumption paths)  
- engines/video_render/tests/test_render_regions.py  
- engines/video_render/tests/test_render_plan_mask.py  
- engines/media_v2/models.py (artifact kind/schema updates only)  
- engines/media_v2/tests/test_media_v2_endpoints.py (only if artifact kinds change)  
- docs/engines/media_program/PHASE_V01_real_detectors_and_artifacts.md  
- docs/engines/video_audio_atomic_design.md (schema/flow notes only)  
- READ-ONLY context: other engine files not listed.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Design & contracts  
  - Update media_v2/models.py to define/confirm artifact kinds `video_region_summary`, `visual_meta`, `asr_transcript` with required meta fields (backend_version, model_used, frame_sample_interval_ms, cache_key, duration_ms) and validation rejecting missing tenant/env.  
  - Document schemas and env flags in docs/engines/video_audio_atomic_design.md and this doc.  
- Regions backend & service (engines/video_regions/backend.py, service.py, routes.py)  
  - Implement RealRegionsBackend: CPU OpenCV/mediapipe face detector (GPU optional), deterministic seeding, min-confidence filter, supports include_regions list.  
  - Enforce key prefix `tenants/{tenant}/{env}/media_v2/{asset_id}/regions/{artifact_id}.png` when registering mask artifacts; no local temp in prod.  
  - Validate RequestContext tenant/env vs payload; reject `t_unknown`/missing.  
  - Add cache key generation and lookup; reuse artifacts when matching backend/version/interval/regions.  
  - Surface clear errors for missing assets, unknown backend, missing deps (skip with stub when allowed).  
- Visual meta (engines/video_visual_meta/backend.py, service.py, routes.py)  
  - Implement backend to sample frames at configurable interval; compute primary_subject_center, shot_boundary (histogram diff), motion magnitude; write `visual_meta` artifact with meta.  
  - Add caching by cache key; reuse artifacts when identical request.  
  - Validate tenant/env, asset existence; include backend_version/model_used in meta.  
- Captions (engines/video_captions/backend.py, service.py, routes.py)  
  - Implement Whisper backend (tiny/base CPU default, GPU optional) with language param; stub fallback when missing deps.  
  - Register `asr_transcript` artifact with timings, language, backend_version, model_used; expose SRT conversion endpoint.  
  - Reject missing tenant/env; enforce RequestContext matching payload.  
- Anonymise (engines/video_anonymise/service.py, routes.py)  
  - Consume region summaries; apply blur strength presets; skip when no faces; tag meta with summary id and backend_version.  
  - Validate tenant/env and asset/summary match.  
- Render consumption (engines/video_render/service.py)  
  - Update region/visual_meta/caption resolution to prefer latest versioned artifacts; keep backward compatibility.  
  - Add plan meta logging selected artifacts and backend versions; dry-run warnings when artifacts missing.  
- Validation & safety  
  - Ensure all services reject missing tenant/env and do not fall back to temp paths in prod; allow dev-only bypass with explicit flag.  
- Fixtures  
  - Add two small video fixtures (face-to-camera, b-roll) for tests; add hashes to avoid drift; guard heavy deps with pytest skips.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

5. Tests  
- engines/video_regions/tests/test_video_regions_service.py: backend selection, artifact shapes, failure surfaces, prefix enforcement.  
- engines/video_regions/tests/test_real_backend.py: deterministic outputs (mocked detectors), cache key behavior, backend_version meta.  
- engines/video_regions/tests/test_video_regions_routes.py: RequestContext vs payload mismatch rejected.  
- engines/video_visual_meta/tests/test_visual_meta_endpoints.py: sampling interval, subject/shot fields, cache reuse.  
- engines/video_captions/tests/test_captions_gen.py: ASR backend selection, artifact meta, SRT conversion; mock whisper to avoid heavy run; reject missing tenant/env.  
- engines/video_anonymise/tests/test_service.py: blur added only when faces exist, meta tagging, failure fallback on missing summary.  
- engines/video_render/tests/test_render_regions.py and test_render_plan_mask.py: consumption of new summaries without breaking legacy schema; dry-run warnings.  
- engines/media_v2/tests/test_media_v2_endpoints.py: artifact kind validation/version fields; rejects missing tenant/env; enforces key prefix.  
Additional required cases:  
- Failure-path tests for missing deps (cv2/whisper) fall back to stub with meta flag.  
- Cache hit/miss tests across regions/visual_meta/captions for param changes.  
- Negative tests for cross-tenant payload vs RequestContext mismatch.

6. Docs & examples  
- Update this phase doc with backend defaults, env flags, schema tables, and textual detector pipeline diagram.  
- Update video_audio_atomic_design.md with artifact schema examples and flow (analyze → anonymise → render).  
- Add a short example: POST /video/regions on face clip → artifact ids; POST /video/anonymise → blurred render plan via /video/render.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If you need a new artifact kind or model field, mark CONTRACT CHANGE in this doc and only update media_v2/models.py and media_v2/tests/test_media_v2_endpoints.py as listed.  
- Keep HTTP signatures stable unless tagged CONTRACT CHANGE here and updated in-lane only.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; do not leave TODOs unless a blocking external dependency is documented.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if you think another file is needed, stop and report instead of editing. Within the allow-list, deliver full Definition of Done with passing tests. Then proceed directly to PHASE_V02 unless blocked by an explicit TODO – HUMAN DECISION REQUIRED.

9. Artifact metadata, caches, and env signals  
- Artifact metadata (populated by `engines/media_v2/models.py`)  
  | Artifact kind | Auto-injected metadata | Notes |
  | --- | --- | --- |
  | `video_region_summary` | `backend_version`, `model_used`, `cache_key`, `duration_ms` | registered mask artifacts must reuse prefix `tenants/{tenant}/{env}/media_v2/{asset_id}/regions/{artifact_id}.png` and include optional `include_regions` hints |
  | `visual_meta` | `backend_version`, `model_used`, `cache_key`, `duration_ms`, `frame_sample_interval_ms` | summary JSON captures `primary_subject_center_{x,y}`, `shot_boundary`, and motion statistics so downstream renders can query `visual_meta` by clip |
  | `asr_transcript` | `backend_version`, `model_used`, `cache_key`, `duration_ms`, `language` | SRT endpoint (`GET /video/captions/{artifact_id}/srt`) materializes clean captions from the transcript artifact |

Media_v2 enforces tenant/env alignment when validating these artifacts and rejects registrations that omit `tenant_id`, `env`, or that violate the cache prefix guardrails.

- Environment flags (override defaults used in CPU-first builds)
  | Flag | Purpose |
  | --- | --- |
  | `VIDEO_REGION_BACKEND` | Real detector selector (default `opencv_face_detector`). Falls back to stub only when deps missing. |
  | `VIDEO_REGIONS_MIN_CONFIDENCE` | Drop detections below this threshold (default ~0.5) to avoid noisy masks. |
  | `VIDEO_VISUAL_META_BACKEND` | Backend used for frame sampling/motion/shot stats (default `opencv_visual_meta`). |
  | `VIDEO_CAPTIONS_BACKEND` | Whisper wrapper name (default `whisper_openai`). |
  | `VIDEO_CAPTIONS_MODEL` | Whisper flavour (`tiny`/`base`/`small`/etc, default `tiny`). |
  | `VIDEO_CAPTIONS_DEVICE` | Execution device (`cpu`/`cuda`, default `cpu`). |
  | `VIDEO_CAPTIONS_LANGUAGE` | Language hint for Whisper (default `en`). |

Cache keys combine tenant+env+asset+(params+backend_version) so repeated requests share the same artifact; metadata exposes `cache_key` plus `backend_version` so render planners can log dependency notices and skip reruns when nothing changed.

10. Pipeline sample & fixtures  
- Worker pipeline (simplified CapCut-lite flow):
  ```
  POST /video/regions              # face + b-roll masks, returns `video_region_summary`
       ↓
  POST /video/visual-meta/analyze  # reuses/creates `visual_meta` summary
       ↓
  POST /video/captions/generate    # writes `asr_transcript`, metadata includes language & cache key
       ↓
  POST /video/anonymise/faces      # consumes latest summary to blur faces
       ↓
  POST /video/render/dry-run       # planner logs `dependency_notices` with backend_version/cache_key
       ↓
  POST /video/render              # final export
       ↓
  GET /video/captions/{artifact_id}/srt  # optional, hydrating final SRT from `asr_transcript`
  ```
  Tests reuse this flow (regions → anonymise → render) to assert artifacts flow and metadata propagate without tenant/env leaks.

- Fixtures for this phase  
  - `tests/fixtures/video_clips/face_clip.mp4` + `face_clip.mp4.sha256` (medium-length face-to-camera clip).  
  - `tests/fixtures/video_clips/broll_clip.mp4` + `broll_clip.mp4.sha256` (motion-heavy B-roll).  
  These fixtures power deterministic backend tests (success/failure, cache hits, cross-tenant validation) and the hashes guard against drift when ffmpeg re-encodes them in CI.
