1. Goal  
Strengthen multicam alignment/auto-cut/highlights/focus automation using real signals for CapCut-lite multicam editing.

North star + Definition of Done  
- North star slice: CapCut-lite multicam + assist for 2–4 camera talking-head/b-roll sets: align cameras, auto-cut, highlight, and focus with minimal manual work.  
- Definition of Done:  
  - Multicam aligns 2–4 cameras via audio cross-corr (LTC optional) with deterministic offsets; auto-cut uses semantic signals (speech/regions/visual_meta).  
  - Assist generates highlight sequence scored by semantics; focus automation uses audio+visual cues; outputs deterministic keyframes.  
  - Tests cover alignment, pacing presets, semantic scoring, fallbacks, and cross-tenant rejection (if applicable); render/timeline compatibility preserved.

2. Scope (In / Out)  
- In: video_multicam alignment + auto-cut, video_assist highlights, video_focus_automation, align helpers, necessary timeline changes for data access.  
- Out: detector backends (handled in V01), core render changes, UI/auth/tenant/safety, new product flows.

3. Modules to touch  
- engines/video_multicam/service.py  
- engines/video_multicam/routes.py  
- engines/video_multicam/align.py (if present)  
- engines/video_multicam/tests/test_multicam_align_endpoints.py  
- engines/video_multicam/tests/test_autocut_smart.py  
- engines/video_multicam/tests/test_multicam_integration.py (only if alignment outputs change)  
- engines/align/audio_text_bars.py (alignment math only)  
- engines/align/tests (if created for cross-corr math)  
- engines/video_assist/service.py  
- engines/video_assist/tests/test_assist_highlights.py  
- engines/video_focus_automation/service.py  
- engines/video_focus_automation/tests/test_focus_automation.py  
- engines/video_timeline/models.py (only if new fields strictly required)  
- engines/video_timeline/service.py (only if new fields strictly required)  
- engines/video_timeline/tests/test_timeline_endpoints.py (only if models change)  
- docs/engines/media_program/PHASE_V04_multicam_assist_focus.md  
- docs/engines/video_audio_atomic_design.md (assist/focus data flow notes only)  
- READ-ONLY context: other engine files not listed.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Design & contracts  
  - Define alignment strategy precedence: LTC/timecode if present, else audio cross-corr; deterministic seed; versioned meta (`alignment_version`, `source_channels`).  
  - Define scoring weights for auto-cut/highlights (speech presence from audio_semantic_timeline, face presence from regions/visual_meta, motion).  
  - Define focus automation keyframe schema (crop_x/crop_y/scale) and meta linking source artifacts.  
- Alignment (video_multicam/service.py, align.py, routes.py)  
  - Implement audio cross-correlation alignment using waveform segments; configurable window/offset limits; deterministic output and meta with confidence/source.  
  - Support optional LTC/timecode inputs; choose best alignment based on confidence; record reason in meta.  
  - Clamp clip offsets to asset durations; validate tenant/env; cache alignment results by session + params.  
- Auto-cut (video_multicam/service.py)  
  - Score segments using speech/activity (audio_semantic_timeline), face presence (regions/visual_meta), and motion; pacing presets (fast/medium/slow) map to target shot lengths; enforce min/max clip lengths.  
  - Generate sequence/tracks deterministically; tag meta with scoring version and inputs used.  
- Highlights (video_assist/service.py)  
  - Rank candidate clips using semantic artifacts; prefer speech + primary subject shots; include meta weights; fallback heuristics only when artifacts missing.  
  - Ensure deterministic ordering and clip timing; clamp to target duration.  
- Focus automation (video_focus_automation/service.py)  
  - Combine audio speech windows + visual subject centers from visual_meta; interpolate keyframes deterministically; fallback to center when artifacts missing.  
  - Validate asset/artifact existence; return automation with meta (source_artifacts, version).  
- Timeline integration (video_timeline models/service)  
  - If new fields needed (scoring meta, alignment offsets), add with backward compatibility; avoid breaking routes.  
- Validation & safety  
  - Reject missing tenant/env; surface clear errors for missing artifacts; log when falling back to stub heuristics.  
- Fixtures  
  - Add test fixtures: synthetic waveforms for alignment; semantic artifacts (audio_semantic_timeline, visual_meta) for scoring; small multicam clip stubs.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

5. Tests  
- engines/video_multicam/tests/test_multicam_align_endpoints.py: cross-corr alignment deterministic on synthetic waveforms; optional LTC path; meta assertions; rejects cross-tenant mismatch if routes enforce RequestContext.  
- engines/video_multicam/tests/test_autocut_smart.py: pacing presets, clip clamping, semantic scoring weights applied; meta includes scoring_version.  
- engines/video_multicam/tests/test_multicam_integration.py: end-to-end session build with alignment + auto-cut; offsets and durations clamped.  
- engines/video_assist/tests/test_assist_highlights.py: scoring with semantic artifacts vs fallback; deterministic ordering.  
- engines/video_focus_automation/tests/test_focus_automation.py: audio+visual combined paths; fallback to center; meta includes sources.  
- engines/align/tests (if added): pure function tests for cross-corr math with mock data to avoid heavy deps.  
- engines/video_timeline/tests/test_timeline_endpoints.py (only if models change): backward compatibility for new meta fields.  
Additional required cases:  
- Negative tests for missing artifacts/assets; cross-tenant mismatch if applicable.  
- Cache hit/miss for alignment reuse when params match.

6. Docs & examples  
- Update this phase doc with alignment algorithm choice, pacing presets, scoring weights, and keyframe schema.  
- Update video_audio_atomic_design.md with assist/focus data flow diagrams.  
- Add example: two-camera interview → align via audio → auto-cut with medium pacing → highlights + focus automation generated.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If you need a new artifact kind or model field, mark CONTRACT CHANGE in this doc and only update explicitly listed files/tests.  
- Keep HTTP signatures stable; tag CONTRACT CHANGE if models change and update only in-lane callsites.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; no TODOs unless a blocking external dependency is documented.

8. Execution note  
Finish this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Deliver full Definition of Done with passing tests, then proceed to the next lane unless blocked by TODO – HUMAN DECISION REQUIRED.
