# Video TODO – CapCut-lite Work Packets

Scope: docs-only registry of feral-worker tasks. Stay within listed folders/files; respect STOP RULEs from phase docs. Lane = Video.

## Stream: Detectors / Artifacts (V01)
- **id:** V01-DETECTOR-CPU-BACKEND  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V01_real_detectors_and_artifacts.md  
  **stream:** Detectors  
  **root_folder:** engines/video_regions/  
  **file_scope:** backend.py, service.py, routes.py, tests/test_video_regions_service.py, tests/test_video_regions_routes.py, tests/test_video_regions_real_backend.py  
  **summary:** Enforce real CPU OpenCV/mediapipe face detector with deterministic seeding, min-confidence filter, and cache-keyed artifacts; reject missing tenant/env and enforce artifact prefix.  
  **definition_of_done:** Real backend loads cascade deterministically; RequestContext tenant/env mismatch rejected; cache hit reuses artifact when params/backend same; mask artifacts use enforced prefix; failing dependencies fall back to stub with meta flag; tests cover cache hit/miss, dependency missing -> stub, tenant/env rejection, min-confidence filtering; update docs/engines/video_audio_atomic_design.md with detector path/meta.  
  **dependencies:** none  
  **agent_scope_hint:** Scope this agent to engines/video_regions/ and listed tests only.  
  **size:** M

- **id:** V01-REGION-ARTIFACT-SCHEMA  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V01_real_detectors_and_artifacts.md  
  **stream:** Detectors  
  **root_folder:** engines/media_v2/  
  **file_scope:** models.py, tests/test_media_v2_endpoints.py  
  **summary:** Harden artifact kinds `video_region_summary` and mask registration meta (backend_version, model_used, cache_key, duration_ms, include_regions) with tenant/env validation and prefix guardrails.  
  **definition_of_done:** Validator rejects missing tenant/env/cache_key/backend_version; enforces mask key prefix; tests assert rejection of missing fields and acceptance of valid payload; no other artifact kinds touched; doc note in docs/engines/video_audio_atomic_design.md updated.  
  **dependencies:** V01-DETECTOR-CPU-BACKEND  
  **agent_scope_hint:** Scope this agent to engines/media_v2/models.py and tests/test_media_v2_endpoints.py only.  
  **size:** S

- **id:** V01-VISUAL-META-REAL-BACKEND  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V01_real_detectors_and_artifacts.md  
  **stream:** Artifacts  
  **root_folder:** engines/video_visual_meta/  
  **file_scope:** backend.py, service.py, routes.py, tests/test_visual_meta_endpoints.py  
  **summary:** Implement OpenCV frame sampler with motion/shot boundary stats, cache keys, and tenant/env validation; persist artifacts with backend_version/model_used/frame_sample_interval_ms meta.  
  **definition_of_done:** Service rejects missing tenant/env and RequestContext mismatch; cache reuse works across identical params; failure path falls back to stub with meta flag; tests cover cache hit/miss, shot boundary flagging, tenant mismatch rejection, backend_version/meta presence; doc note in video_audio_atomic_design.md updated.  
  **dependencies:** none  
  **agent_scope_hint:** Scope to engines/video_visual_meta/ files listed.  
  **size:** M

- **id:** V01-CAPTIONS-WHISPER-STUB-GUARD  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V01_real_detectors_and_artifacts.md  
  **stream:** Captions  
  **root_folder:** engines/video_captions/  
  **file_scope:** backend.py, service.py, routes.py, tests/test_captions_gen.py, tests/test_real_backend.py  
  **summary:** Wire Whisper backend selection (tiny/base CPU default) with deterministic stub fallback, cache keys, language parameter, and artifact meta; enforce tenant/env on routes.  
  **definition_of_done:** POST generates `asr_transcript` with backend_version/model_used/cache_key/language meta; cache hit reuse verified; missing deps triggers stub meta flag; tenant/env mismatch rejected; SRT endpoint returns ordered captions; tests assert these behaviors; doc note in video_audio_atomic_design.md updated.  
  **dependencies:** none  
  **agent_scope_hint:** Scope to engines/video_captions/ and listed tests.  
  **size:** M

- **id:** V01-ANONYMise-BLUR-CONSUME-REGIONS  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V01_real_detectors_and_artifacts.md  
  **stream:** Anonymise  
  **root_folder:** engines/video_anonymise/  
  **file_scope:** service.py, routes.py, tests/test_video_anonymise_service.py  
  **summary:** Consume latest `video_region_summary` artifacts, apply blur strengths, tag meta with summary_id/backend_version, and reject tenant/env mismatches.  
  **definition_of_done:** Service loads summary by id, rejects cross-tenant/env, skips when no faces, returns artifact meta with summary_id/backend_version; tests cover blur applied/not applied, tenant mismatch, missing summary; doc note in video_audio_atomic_design.md updated.  
  **dependencies:** V01-DETECTOR-CPU-BACKEND  
  **agent_scope_hint:** Scope to engines/video_anonymise/ files listed.  
  **size:** S

- **id:** V01-RENDER-CONSUME-ARTIFACTS  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V01_real_detectors_and_artifacts.md  
  **stream:** Artifacts  
  **root_folder:** engines/video_render/  
  **file_scope:** service.py, tests/test_render_regions.py, tests/test_render_plan_mask.py  
  **summary:** Render planner prefers latest region/visual_meta/caption artifacts, logs dependency_notices with backend_version/cache_key, and warns on missing artifacts.  
  **definition_of_done:** Plan meta includes dependency_notices for each artifact type; missing artifacts emit warnings not silent skips; tests assert dependency_notices content, warnings when artifacts absent, backward compatibility; no other render behavior altered.  
  **dependencies:** V01-DETECTOR-CPU-BACKEND, V01-VISUAL-META-REAL-BACKEND, V01-CAPTIONS-WHISPER-STUB-GUARD  
  **agent_scope_hint:** Scope to engines/video_render/service.py and listed tests.  
  **size:** S

## Stream: FX / Quality (V02)
- **id:** V02-TRANSITION-VALIDATION  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V02_fx_transitions_quality.md  
  **stream:** FX/Transitions  
  **root_folder:** engines/video_render/  
  **file_scope:** planner.py, service.py, tests/test_render_filters_transitions.py  
  **summary:** Enforce transition catalog mapping to xfade/acrossfade with duration clamps and deterministic ordering; reject unknown transitions.  
  **definition_of_done:** Unknown transition raises ValueError; transitions sorted by start_ms/id; plan meta records video_alias/audio_alias; tests assert mapping, clamping, ordering, and rejection of unknown type; doc table in video_audio_atomic_design.md refreshed.  
  **dependencies:** none  
  **agent_scope_hint:** Scope to engines/video_render/planner.py, service.py, tests/test_render_filters_transitions.py.  
  **size:** S

- **id:** V02-MASK-AWARE-FILTERS  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V02_fx_transitions_quality.md  
  **stream:** FX  
  **root_folder:** engines/video_render/  
  **file_scope:** service.py, tests/test_render_masked_filters.py, tests/test_render_plan_mask.py  
  **summary:** Ensure region-aware filters (teeth_whiten/skin_smooth/eye_enhance/face_blur/lut) split streams, apply mask via alphamerge, and validate params.  
  **definition_of_done:** Mask-aware path exercised in tests; invalid params clamped/rejected; plan graph shows mask usage; tests assert masked filter inclusion and parameter validation; doc update with mask-aware note.  
  **dependencies:** V01-RENDER-CONSUME-ARTIFACTS  
  **agent_scope_hint:** Scope to engines/video_render/service.py and listed tests.  
  **size:** M

- **id:** V02-SLOWMO-PRESETS-FALLBACK  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V02_fx_transitions_quality.md  
  **stream:** FX  
  **root_folder:** engines/video_render/  
  **file_scope:** service.py, tests/test_render_slowmo.py  
  **summary:** Implement slowmo quality presets (high/medium/fast) with optical flow where available and tblend fallback; record slowmo_details meta.  
  **definition_of_done:** Plan meta has slowmo_details per clip; missing optical flow triggers fast/tblend with warning; tests assert preset mapping and meta; defaults deterministic.  
  **dependencies:** none  
  **agent_scope_hint:** Scope to engines/video_render/service.py and tests/test_render_slowmo.py.  
  **size:** S

- **id:** V02-STABILISE-DEFAULTS-META  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V02_fx_transitions_quality.md  
  **stream:** FX  
  **root_folder:** engines/video_stabilise/  
  **file_scope:** backend.py, service.py, tests/test_render_stabilise.py  
  **summary:** Apply deterministic stabilise defaults (smoothing/zoom/crop/tripod), consume transform artifacts when present, and surface stabilise_warnings meta when missing.  
  **definition_of_done:** Defaults enforced; transform artifact used if available; warnings emitted when missing; tests assert defaults, warning behavior, and meta presence.  
  **dependencies:** none  
  **agent_scope_hint:** Scope to engines/video_stabilise/ and listed tests.  
  **size:** S

## Stream: Render / Proxies / Jobs / Preview (V03)
- **id:** V03-HW-DETECTION-FALLBACK  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V03_render_preview_hardening.md  
  **stream:** Render/Jobs  
  **root_folder:** engines/video_render/  
  **file_scope:** ffmpeg_runner.py, service.py, tests/test_render_service.py  
  **summary:** Detect hardware encoders (nvenc/videotoolbox) once per process with cache and deterministic CPU fallback; expose selection in plan meta.  
  **definition_of_done:** Hardware detection cached; env override supported; plan meta records encoder choice; tests mock presence/absence and assert selection/fallback/meta; no actual ffmpeg run required.  
  **dependencies:** none  
  **agent_scope_hint:** Scope to engines/video_render/ffmpeg_runner.py, service.py, tests/test_render_service.py.  
  **size:** M

- **id:** V03-PROXY-ARTIFACT-META  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V03_render_preview_hardening.md  
  **stream:** Proxies  
  **root_folder:** engines/video_render/  
  **file_scope:** service.py, tests/test_render_proxies.py  
  **summary:** Enforce proxy ladder generation with cache keys (asset+profile), artifact meta (profile, hw_encoder_used, source_asset_id), and prefix; reuse existing proxies when matching.  
  **definition_of_done:** ensure_proxies_for_project reuses on cache hit; artifacts carry required meta and tenant/env; tests assert reuse, meta fields, prefix enforcement, and cache key changes trigger regen.  
  **dependencies:** V03-HW-DETECTION-FALLBACK  
  **agent_scope_hint:** Scope to engines/video_render/service.py and tests/test_render_proxies.py.  
  **size:** M

- **id:** V03-JOBS-RESUME-CANCEL  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V03_render_preview_hardening.md  
  **stream:** Jobs  
  **root_folder:** engines/video_render/  
  **file_scope:** jobs.py, service.py, tests/test_render_jobs.py, tests/test_chunked_render.py  
  **summary:** Implement job state transitions (queued/running/failed/cancelled/completed), resume/cancel semantics, idempotent job_id on duplicates, and backpressure limit.  
  **definition_of_done:** jobs.py supports transition guards and backpressure setting; duplicate job with different params rejected; cancel cleans partial outputs; tests cover transitions, idempotency, cancel/resume, backpressure; metadata unaffected elsewhere.  
  **dependencies:** V03-HW-DETECTION-FALLBACK  
  **agent_scope_hint:** Scope to engines/video_render/jobs.py, service.py, tests/test_render_jobs.py, tests/test_chunked_render.py.  
  **size:** M

- **id:** V03-RENDER-ERROR-TAXONOMY  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V03_render_preview_hardening.md  
  **stream:** Render/Errors  
  **root_folder:** engines/video_render/  
  **file_scope:** service.py, ffmpeg_runner.py, tests/test_render_service.py  
  **summary:** Surface structured errors with stage/context/stderr tail; no silent skips on missing assets; dry-run warns clearly.  
  **definition_of_done:** Exceptions include stage/stderr tail; missing asset/artifact produces specific warning; tests assert error shape and dry-run warnings; no behavior change to successful path.  
  **dependencies:** none  
  **agent_scope_hint:** Scope to engines/video_render/service.py, ffmpeg_runner.py, tests/test_render_service.py.  
  **size:** S

- **id:** V03-PREVIEW-PROXY-ENFORCEMENT  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V03_render_preview_hardening.md  
  **stream:** Preview  
  **root_folder:** engines/video_preview/  
  **file_scope:** service.py, tests/test_preview.py  
  **summary:** Preview service must enforce proxy usage when available, attach preview_warnings, and select draft/preview profiles deterministically.  
  **definition_of_done:** get_preview_stream selects proxy profile, warns when proxies missing/generation fails, returns render_plan meta with preview_warnings and preview_profile; tests assert warnings, profile selection, and behavior when tracks/clips absent.  
  **dependencies:** V03-PROXY-ARTIFACT-META  
  **agent_scope_hint:** Scope to engines/video_preview/service.py and tests/test_preview.py.  
  **size:** S

- **id:** V03-RENDER-PLAN-DETERMINISM  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V03_render_preview_hardening.md  
  **stream:** Render  
  **root_folder:** engines/video_render/  
  **file_scope:** service.py, planner.py, tests/test_render_plan_compositing.py  
  **summary:** Ensure plan ordering (filters/transitions/automation) is deterministic; plan meta logs render_profile/hardware/slowmo/stabilise selections.  
  **definition_of_done:** Same inputs produce identical plan string/hash; meta includes profile and hardware; tests assert deterministic ordering and meta presence; no change to actual ffmpeg execution.  
  **dependencies:** V03-HW-DETECTION-FALLBACK  
  **agent_scope_hint:** Scope to engines/video_render/service.py, planner.py, tests/test_render_plan_compositing.py.  
  **size:** M

## Stream: Multicam / Assist / Focus (V04)
- **id:** V04-ALIGN-CROSSCORR  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V04_multicam_assist_focus.md  
  **stream:** Multicam  
  **root_folder:** engines/video_multicam/  
  **file_scope:** backend.py, service.py, tests/test_multicam_align_endpoints.py, tests/test_align_real.py  
  **summary:** Implement deterministic audio cross-correlation alignment with configurable window/offset, cache key, and meta (alignment_version/confidence); enforce tenant/env.  
  **definition_of_done:** Alignment returns offsets with meta; cache hit reuse; RequestContext mismatch rejected; tests cover synthetic waveforms, cache reuse, tenant rejection; doc note in video_audio_atomic_design.md updated.  
  **dependencies:** none  
  **agent_scope_hint:** Scope to engines/video_multicam/ backend.py, service.py, listed tests.  
  **size:** M

- **id:** V04-AUTOCUT-SEMANTIC-SCORING  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V04_multicam_assist_focus.md  
  **stream:** Multicam  
  **root_folder:** engines/video_multicam/  
  **file_scope:** service.py, tests/test_multicam_auto_cut_endpoints.py, tests/test_autocut_smart.py  
  **summary:** Score segments using speech/activity (audio_semantic_timeline), face presence (regions/visual_meta), motion; pacing presets map to target shot lengths; deterministic sequence output.  
  **definition_of_done:** Auto-cut uses semantic artifacts when available, logs scoring_version/meta, clamps shot lengths; tests assert use of semantics vs fallback, pacing presets, deterministic output; RequestContext respected.  
  **dependencies:** V01-RENDER-CONSUME-ARTIFACTS, V04-ALIGN-CROSSCORR  
  **agent_scope_hint:** Scope to engines/video_multicam/service.py and listed tests.  
  **size:** M

- **id:** V04-ASSIST-HIGHLIGHTS-SCORING  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V04_multicam_assist_focus.md  
  **stream:** Assist  
  **root_folder:** engines/video_assist/  
  **file_scope:** service.py, tests/test_assist_highlights.py  
  **summary:** Use semantic artifacts (audio_semantic_timeline + visual_meta) to rank highlights with meta weights/pacing; deterministic ordering; cache by params.  
  **definition_of_done:** Highlights include meta weights and cache key; falls back with logged warning when artifacts missing; tests assert cache reuse, deterministic ordering, and artifact-driven scoring; RequestContext respected.  
  **dependencies:** V01-VISUAL-META-REAL-BACKEND, V04-AUTOCUT-SEMANTIC-SCORING  
  **agent_scope_hint:** Scope to engines/video_assist/service.py and tests/test_assist_highlights.py.  
  **size:** S

- **id:** V04-FOCUS-AUTOMATION-SEMANTIC  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V04_multicam_assist_focus.md  
  **stream:** Focus  
  **root_folder:** engines/video_focus_automation/  
  **file_scope:** service.py, tests/test_focus_automation.py, tests/test_focus.py  
  **summary:** Combine audio speech windows + visual_meta subject centers to emit deterministic keyframes (position_x/position_y/scale); fallback to center when missing.  
  **definition_of_done:** Automation uses semantic artifacts when present, includes meta with source_artifacts/version, rejects tenant/env mismatch; tests assert semantic path, fallback path, deterministic output, meta content.  
  **dependencies:** V01-VISUAL-META-REAL-BACKEND  
  **agent_scope_hint:** Scope to engines/video_focus_automation/ and listed tests.  
  **size:** S

- **id:** V04-TIMELINE-COMPAT-FIELDS  
  **status:** DONE
  **lane:** Video  
  **phase:** PHASE_V04_multicam_assist_focus.md  
  **stream:** Multicam/Timeline  
  **root_folder:** engines/video_timeline/  
  **file_scope:** models.py, service.py, tests/test_timeline_endpoints.py  
  **summary:** Add/confirm fields needed by multicam/assist (scoring meta/alignment offsets) with backward compatibility and RequestContext validation.  
  **definition_of_done:** New fields optional with defaults; existing routes unaffected; tests cover new fields persistence and backward compatibility; no other models touched.  
  **dependencies:** V04-AUTOCUT-SEMANTIC-SCORING  
  **agent_scope_hint:** Scope to engines/video_timeline/ models/service and tests/test_timeline_endpoints.py.  
  **size:** S
