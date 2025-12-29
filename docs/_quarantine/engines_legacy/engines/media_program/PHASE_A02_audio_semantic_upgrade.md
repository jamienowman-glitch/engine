1. Goal  
Upgrade semantic timeline (ASR/VAD/beats) to real signals with caching, deterministic slicing, and better audio→video origin mapping to power DAW-lite + video alignment.

North star + Definition of Done  
- North star slice: Ableton/Bandlab-lite semantic layer that turns field recordings/podcasts into reusable speech/music/silence + beats artifacts aligned to clips, consumable by video without hacks.  
- Definition of Done:  
  - audio_semantic_timeline uses real ASR/VAD/beat backends (whisper+librosa default) with cache keys and versioned meta; stub fallback deterministic.  
  - By-clip slicing returns clip-relative events/beats with documented speed-change limitation.  
  - audio_to_video_origin uses semantics to map shots; meta records semantic influence.  
  - Tests cover success/failure, caching, clipping, cross-tenant rejection (if applicable), and origin mapping; docs include schemas and examples.

2. Scope (In / Out)  
- In: audio_semantic_timeline backend, audio_to_video_origin mapping, audio_voice_phrases if transcripts used, media_v2 artifacts/meta for semantics.  
- Out: render/fx (prior phase), UI/auth/tenant/safety, orchestration.

3. Modules to touch  
- engines/audio_semantic_timeline/service.py  
- engines/audio_semantic_timeline/models.py  
- engines/audio_semantic_timeline/routes.py  
- engines/audio_semantic_timeline/tests/test_audio_semantic_timeline_endpoints.py  
- engines/audio_semantic_timeline/tests/test_audio_semantic_caching.py  
- engines/audio_semantic_timeline/tests/test_a02_semantics.py  
- engines/audio_to_video_origin/service.py  
- engines/audio_to_video_origin/tests (create/extend for mapping)  
- engines/audio_voice_phrases/service.py (only if transcript consumption changes)  
- engines/audio_voice_phrases/tests/test_phrases.py (only if service changes)  
- engines/media_v2/models.py (only if artifact kind/meta change)  
- engines/media_v2/tests/test_media_v2_endpoints.py (only if artifact kind/meta change)  
- docs/engines/media_program/PHASE_A02_audio_semantic_upgrade.md  
- docs/engines/video_audio_atomic_design.md (semantic artifact usage notes only)  
- READ-ONLY context: other files.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Design & schemas  
  - Define artifact schema fields for `audio_semantic_timeline` (events/beats/meta: backend_version, semantic_version, cache_key, include_beats/speech/music flags, loudness_window_ms, min_silence_ms, transcription, confidence).  
  - Specify cache key formula (asset|artifact|params|backend_version|user_id) in service/models.  
  - Document env flags: `AUDIO_SEMANTIC_BACKEND` (whisper_librosa|stub), `AUDIO_SEMANTIC_WHISPER_MODEL`, `AUDIO_SEMANTIC_SEED`.  
- Backend implementation (service.py/backend internals)  
  - Implement whisper+librosa backend: ASR with language param, VAD/speech/music detection, beat tracking; deterministic ordering (seed) and loudness/energy fields.  
  - Stub backend: deterministic speech/music/silence pattern + beats for missing deps; meta.backend_type="stub".  
  - Attach backend_version/model_used; reject missing tenant/env if routes enforce it.  
- Caching  
  - Add cache lookup by cache key; reuse artifacts when identical params; record cache hits/misses in meta.  
- Clip slicing  
  - By-clip endpoint slices events/beats to clip window with clip-relative timestamps; mark clip_relative=True; document speed-change limitation in meta and docs.  
- audio_to_video_origin  
  - Use latest semantic artifacts to refine source windows (speech start, beat alignment); include semantic_version/cache_key in VideoShot meta.  
  - Validate asset/artifact existence; clear errors for missing semantics.  
- Validation & safety  
  - Reject missing deps by falling back to stub with meta flag; surface clear errors for unsupported params; reject cross-tenant payloads if routes carry RequestContext.  
- Fixtures  
  - Add lightweight audio fixtures (speech+music) for tests; guard heavy deps with skips.  
- Docs sync  
  - Update schema definitions, cache key formula, and backend defaults in this doc and video_audio_atomic_design.md.  

5. Tests  
- engines/audio_semantic_timeline/tests/test_audio_semantic_timeline_endpoints.py: cache hit/miss, backend selection (mocked), meta fields, rejection on missing params/tenant if applicable.  
- engines/audio_semantic_timeline/tests/test_audio_semantic_caching.py: cache key correctness when params change; ensures reuse.  
- engines/audio_semantic_timeline/tests/test_a02_semantics.py: ASR/VAD/beat outputs (mocked), clip slicing to windows, stub fallback path.  
- engines/audio_to_video_origin/tests: mapping uses semantic offsets, meta reflects semantic_version/cache_key, handles missing semantics gracefully.  
- engines/audio_voice_phrases/tests/test_phrases.py: compatibility with new transcript fields if consumed.  
- engines/media_v2/tests/test_media_v2_endpoints.py (only if schema changed): artifact validation/version fields.  
Additional required cases:  
- Negative tests for missing deps (whisper/librosa) triggering stub with meta flag.  
- Determinism test: same input/params -> identical events/beats/cache_key.  
- Speed-change limitation noted in meta/warning test.  
- Cross-tenant mismatch rejected (if RequestContext enforced).

6. Docs & examples  
- Update this phase doc with backend defaults, cache key formula, artifact schema tables, limitations, and example request/response payloads.  
- Update video_audio_atomic_design.md to reflect semantic artifact usage and origin mapping.  
- Add example: analyze audio asset → semantic artifact id; by-clip slice for timeline clip; audio_to_video_origin produces shot list with semantic offsets (include sample JSON).

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If you need a new artifact kind or model field, mark CONTRACT CHANGE in this doc and only update media_v2/models.py and media_v2/tests/test_media_v2_endpoints.py as listed.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; no TODOs unless a blocking external dependency is documented.

8. Execution note  
Finish this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Within the allow-list, deliver full Definition of Done with passing tests. Then move to PHASE_A03 unless a TODO – HUMAN DECISION REQUIRED truly blocks you.

9. Runtime notes & contracts  

**Artifact schema**  
- `AudioEvent`: `{kind: speech|music|silence|other, start_ms, end_ms, loudness_lufs?, confidence?, transcription?, speaker_id?, meta?}` so downstream consumers can gauge the confidence/loudness of each span.  
- `BeatEvent`: `{time_ms, beat_index?, bar_index?, subdivision?}`; beats are sorted by time and are clipped with `time_ms` relative to whatever window is returned (full asset or clip).  
- `AudioSemanticTimelineSummary`: the stored JSON contains `asset_id`, optional `artifact_id`, `duration_ms`, `events`, `beats`, and a `meta` map that now always declares: `model_used`, `backend`, `backend_version`, `backend_type`, `semantic_version`, the request flags (`include_beats`, `include_speech_music`, `min_silence_ms`, `loudness_window_ms`), `speed_change_limit`, and `audio_semantic_cache_key`. Each artifact also embeds `backend_info` (a `service/backend_version/dependencies` snapshot from `build_backend_health_meta`).  

**Cache key formula**  
- `audio_semantic_cache_key = tenant_id|env|asset_id|artifact_id|include_beats|include_speech_music|min_silence_ms|loudness_window_ms|backend_version|user_id_or_anonymous`.  
- Identical requests reuse the same `audio_semantic_timeline` artifact and emit `result.meta.cache_hit=true`; different users or params produce deterministic fallback runs.  

**Environment flags**  
- `AUDIO_SEMANTIC_BACKEND` chooses between `whisper_librosa` (default) and `stub`.  
- `AUDIO_SEMANTIC_WHISPER_MODEL` defaults to `tiny` and is forwarded to Whisper.  
- `AUDIO_SEMANTIC_SEED` defaults to `42` so librosa beat detection/loudness sampling remain deterministic across runs.  
- Missing dependencies (librosa/whisper) trigger the deterministic stub backend (`meta.backend_type="stub"`, `meta.semantic_version="audio_semantic_stub_v1"`); the service still returns the same artifact contract but marks the backend via `meta.backend`/`backend_type`.  

**Clip slicing contract**  
- `GET /audio/semantic-timeline/by-clip/{clip_id}` reuses the registered semantic artifact for the clip’s asset and trims the stored events/beats to the clip window.  
- Returned events/beats are in clip-relative milliseconds and `summary.meta` adds `clip_window_ms`, `clip_relative=true`, `speed_change_limit=1.05`, `speed_change=clip.speed`, and `speed_change_limited` (true when `speed != 1`).  
- The `speed_change_limit` is documented so downstream render/automation systems can decide whether a clip’s playrate falls within safe bounds.  

**Audio→Video origin mapping**  
- `AudioToVideoOriginService` prefers the latest `audio_semantic_timeline` artifact for each source asset, reads its `events` to detect the first speech window, and biases each `VideoShot.source_start_ms` by that `semantic_offset_ms`.  
- Each `VideoShot.meta` now retains `semantic_version`, `semantic_cache_key`, and `semantic_offset_ms` while preserving any `source_asset_id`/`source_start_ms` overrides from upstream artifacts.  
- The emitted `ShotListResult.meta` echoes the most recent `semantic_cache_key`/`semantic_version` seen so downstream planners can detect reuse or stale tickets.  

**Example flow**  
1. `POST /audio/semantic-timeline/analyze` (`tenant_id=t1`, `env=dev`, `asset_id=a123`, `user_id=u1`, `include_beats=true`, `include_speech_music=true`): returns `{audio_semantic_artifact_id, uri, meta}` with `meta = {cache_key: "t1|dev|a123|None|True|True|300|1000|whisper_librosa_v2|u1", cache_hit: false, backend_type: "whisper_librosa", audio_semantic_cache_key: "...", backend_info: {...}}`.  
2. `GET /audio/semantic-timeline/by-clip/{clip_id}` uses the same artifact and replies with `summary.meta.clip_relative=true` plus `clip_window_ms` and `speed_change_limit=1.05`.  
3. `POST /audio/to-video-origin` (via `ShotListRequest`) yields `ShotListResult` containing `shots`: each `VideoShot` records `semantic_offset_ms` (first speech event), `semantic_version`, `semantic_cache_key`, and `target_duration_ms`; `result.meta.semantic_cache_key` echoes the artifact hash so rendering or caching layers know which semantics influenced the list.  

**Limitations & troubleshooting**  
- Input validation still rejects unknown tenants/envs (`ValueError` surfaced to routes) and clamps `min_silence_ms`/`loudness_window_ms` to guarded ranges.  
- If Whisper/Librosa are missing, the stub backend guarantees deterministic speech/music/silence cycles but logs the dependency error in `result.meta.backend_info.dependencies.librosa.error`.  
- Ensure downstream callers persist every `audio_semantic_cache_key` they observe so the cache stays consistent; duplicate artifacts are harmless but may cause re-registration if `cache_key` isn’t reused.  
