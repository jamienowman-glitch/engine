# Phase P10 – Cross-Modal Link Back to Video

Goal: Maintain deterministic mappings from audio samples/loops back to their source video/time ranges and generate shot lists aligned to audio patterns.

Scope
- In: audio_to_video_origin engine, mapping store between audio artifacts and source asset windows, helpers to build video shot lists aligned to audio patterns, docs/tests.
- Out: changing video rendering/timeline behavior, UI, auth/spine/connectors; no new video contracts unless marked CONTRACT CHANGE.

Modules / files to touch
- engines/audio_to_video_origin/service.py, models.py
- Mapping storage using media_v2 artifact meta or dedicated repo (data-only)
- Helper to emit shot list data (not executing video render)
- engines/audio_pattern_engine integration to read mappings
- Tests under engines/audio_to_video_origin/tests
- Docs: docs/engines/audio_program/PHASE_P10_audio_to_video_origin.md

Implementation steps
1) Mapping model: OriginMap {audio_artifact_id, parent_asset_id, source_start_ms, source_end_ms, clip_offsets?}; ensure created when field_to_samples registers artifacts (if missing, add sidecar registration—mark CONTRACT CHANGE if shape changes).
2) APIs: store/retrieve mappings; given PatternTimeline (from pattern_engine), build shot list: [{asset_id, start_ms, end_ms, target_time_on_pattern}] preserving deterministic order.
3) No video execution: output data only; video team can consume shot list later. Keep format simple (JSON) with meta {backend_version, pattern_id, seed}.
4) Determinism: identical inputs yield same shot list; handle missing mappings with explicit errors.
5) Docs: describe how to consume shot lists; do not alter video_timeline contracts.

Tests
- Happy: mapping retrieval and shot list generation for pattern with known artifacts; verify timing alignment to pattern clip starts.
- Edge: missing mapping (error), overlapping mappings, patterns using artifacts from multiple assets; ensure shot list stays sorted by pattern time.
- Determinism: repeated run yields identical shot list.

Safety / non-goals
- No changes to video render/timeline behavior; no UI.
- No tenant/auth changes; if multi-tenant concerns arise, add comment `# NOTE: tenant/user scoping deferred – will integrate with core spine later.` and proceed with data-only logic.

On completion of Phase P10:
- Immediately proceed to Phase P11 using its phase doc.
- Do not pause for human review unless tests fail or you hit an explicit TODO/STOP marker.
