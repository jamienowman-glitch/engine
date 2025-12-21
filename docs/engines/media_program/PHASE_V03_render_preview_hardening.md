1. Goal  
Harden render/preview pipeline with GPU-aware profiles, proxy ladder, chunk/job reliability, and clear error surfacing for CapCut-lite editing.

North star + Definition of Done  
- North star slice: CapCut-lite render/preview for 2–3 track projects with GPU/CPU parity, proxy ladder, resumable jobs, and deterministic plans.  
- Definition of Done:  
  - Render profiles cover draft/preview/social/master with GPU/CPU variants; hardware detection with deterministic fallback.  
  - Proxy ladder auto-generates/uses proxies; chunked jobs resumable/cancellable with backpressure; clear errors with context.  
  - Preview service uses proxies and draft profiles; missing assets handled gracefully with warnings.  
  - Tests cover success/failure for proxies/jobs/hardware selection; media_v2 artifacts carry profile/hw meta; no prod fallback to temp paths.

2. Scope (In / Out)  
- In: video_render job handling, ffmpeg runner/profile selection, proxy creation/lookup, preview service strategies, error logging.  
- Out: detectors/anonymise, UI, auth/tenant/safety, orchestration outside render jobs.

3. Modules to touch  
- engines/video_render/service.py  
- engines/video_render/ffmpeg_runner.py  
- engines/video_render/profiles.py  
- engines/video_render/jobs.py  
- engines/video_render/tests/test_render_proxies.py  
- engines/video_render/tests/test_render_jobs.py  
- engines/video_render/tests/test_render_service.py  
- engines/video_render/tests/test_chunked_render.py  
- engines/video_preview/service.py  
- engines/video_preview/tests/test_preview.py  
- engines/media_v2/models.py (only if proxy artifact kinds/meta change)  
- engines/media_v2/tests/test_media_v2_endpoints.py (only if proxy artifact kinds/meta change)  
- docs/engines/media_program/PHASE_V03_render_preview_hardening.md  
- docs/engines/video_audio_atomic_design.md (proxy/job flow notes only)  
- READ-ONLY context: other engine files not listed.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Design & contracts  
  - Extend profiles.py with explicit profiles: DRAFT_360p/480p, PREVIEW_720p, SOCIAL_1080p, MASTER_4k, each with fps/codec/pix_fmt/audio_bitrate/threading; GPU/CPU variants and mapping rules.  
  - Define proxy artifact meta fields (profile_name, source_asset_id, hw_encoder_used) in media_v2/models.py if needed; enforce tenant/env validation.  
  - Define job state transitions and backpressure limits in jobs.py (QUEUED/RUNNING/FAILED/CANCELED/COMPLETED) with idempotent job_id handling.  
- Hardware detection & profile selection (ffmpeg_runner.py, service.py)  
  - Implement hardware encoder discovery (nvenc/videotoolbox) once per process; cache result; allow env override to force CPU/GPU; deterministic fallback to CPU.  
  - Map profiles to available encoders; include selection in plan meta.  
- Proxy ladder (service.py)  
  - Implement ensure_proxies_for_project/sequence: detect missing proxies for clips, queue proxy renders using draft profile, reuse existing proxies via cache key (asset_id+profile).  
  - Enforce key prefix `tenants/{tenant}/{env}/media_v2/{asset_id}/proxy_{profile}.mp4`; no temp fallback in prod.  
  - Register proxy artifacts with meta (profile, hw_encoder_used, source_asset_id).  
- Chunk/job robustness (service.py, jobs.py)  
  - Implement resume/cancel semantics: partial outputs cleaned, retries limited; job repo persists state; backpressure guard (max concurrent jobs).  
  - Add deterministic job id generation; reject duplicate job with different params.  
  - Add timeouts per chunk; failure surfaces FFmpegError with stage/context/stderr tail.  
- Render plan determinism (service.py)  
  - Ensure input ordering, filter/transition ordering, speed/automation order stable; include selected profiles/hardware in plan meta.  
  - Dry-run reports missing artifacts/assets clearly; never silent skip.  
- Preview service (video_preview/service.py)  
  - Select draft/preview profile based on strategy; force proxy usage; warn on missing proxies and fall back to draft full-res when allowed.  
  - Return plan preview + estimated latency; propagate errors from render.  
- Validation & safety  
  - Reject missing tenant/env; no prod fallback to local temp paths; allow dev-only guard behind flag.  
  - Structured errors with remediation hints for missing ffmpeg/hw encoder.  
- Fixtures  
  - Add small fixtures for proxy generation and chunk rendering; guard heavy ffmpeg with skips when hw encoders missing.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

5. Tests  
- engines/video_render/tests/test_render_proxies.py: proxy lookup/generation, cache key reuse, prefix enforcement.  
- engines/video_render/tests/test_render_jobs.py: resume/cancel/idempotency, status transitions, backpressure limits, duplicate job rejection.  
- engines/video_render/tests/test_render_service.py: hardware encoder selection (mocked), error surfacing includes context/stderr tail.  
- engines/video_render/tests/test_chunked_render.py: partial chunk cleanup, deterministic ordering, timeout handling.  
- engines/video_preview/tests/test_preview.py: draft/preview profile selection, proxy enforcement, missing asset handling with warnings.  
- engines/media_v2/tests/test_media_v2_endpoints.py: proxy artifact validation/meta if schema touched.  
Additional required cases:  
- Mocked hw detection paths for nvenc/videotoolbox present/absent.  
- Failure-path tests for ffmpeg error bubbles up with stage context.  
- Dry-run warns on missing artifacts/assets.

6. Docs & examples  
- Update this phase doc with profile matrix, proxy policy, job state machine, and error taxonomy.  
- Update video_audio_atomic_design.md to include proxy ladder, job flow, and plan meta examples.  
- Add example flow: project with two clips -> proxies generated -> render job queued/resumed -> preview plan returned.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If you need a new artifact kind or model field, mark CONTRACT CHANGE in this doc and only update media_v2/models.py and media_v2/tests/test_media_v2_endpoints.py as listed.  
- Keep HTTP signatures stable unless tagged CONTRACT CHANGE and updated in-lane.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; no TODOs unless a blocking external dependency is documented.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Within the allow-list, deliver full Definition of Done with passing tests. Then proceed to PHASE_V04 unless blocked by TODO – HUMAN DECISION REQUIRED.
