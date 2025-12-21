1. Goal  
Add DAW-ish ergonomics: automation breadth, fades/crossfades, bus/stem exports, mix/export presets, and deterministic render planning to deliver podcast/music masters and stems.

North star + Definition of Done  
- North star slice: DAW-lite timeline/mix where a worker can build a sequence with automation/fades, route tracks to buses, and export masters/stems for podcast or music with predictable loudness/metadata.  
- Definition of Done:  
  - Timeline models support clip/track automation (gain/pan/filter), fades/crossfades with validation.  
  - Mix bus presets for dialogue/music/fx/ambience with role-based routing; stems export toggle with metadata.  
  - Export presets (podcast/music/VO/draft) define limiter/loudness/dither/headroom; render planner applies deterministically.  
  - Artifacts registered with bus/preset meta; tests cover automation application, fades, stems, and plan determinism.

2. Scope (In / Out)  
- In: audio_timeline, audio_render planner/service, audio_mix_buses, arrangement/structure integration for roles/markers.  
- Out: backend dependency checks, UI/auth/tenant/safety, orchestration.

3. Modules to touch  
- engines/audio_timeline/models.py  
- engines/audio_timeline/service.py  
- engines/audio_timeline/tests/test_timeline.py  
- engines/audio_render/planner.py  
- engines/audio_render/service.py  
- engines/audio_render/models.py (only if fields strictly required)  
- engines/audio_render/tests/test_a04_mix.py  
- engines/audio_render/tests/test_render_stems.py  
- engines/audio_mix_buses/service.py  
- engines/audio_mix_buses/tests/test_buses.py  
- engines/audio_arrangement_engine/service.py (only if role propagation needed)  
- engines/audio_arrangement_engine/tests/test_arrangement.py (only if service changes)  
- engines/audio_structure_engine/service.py (markers/roles only if needed)  
- engines/audio_structure_engine/tests/test_structure.py (only if touched)  
- docs/engines/media_program/PHASE_A04_dawish_timeline_mix.md  
- docs/engines/ENGINE_INVENTORY.md (only if artifact/meta fields change)  
- READ-ONLY context: all other files.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Timeline models/service  
  - Add/confirm per-clip and per-track automation fields (gain/pan/filter) with ordered keyframes; validate time ordering and bounds (clip duration).  
  - Add fade in/out curves and optional crossfade hints; enforce sum of fades ≤ clip duration; surface ValueError on violations.  
  - Persist automation/fade fields; maintain backward compatibility for existing routes.  
- Mix buses (audio_mix_buses/service.py)  
  - Define bus presets for roles (dialogue/music/fx/ambience) with default gain/pan/EQ; map tracks by role tags; deterministic ordering.  
  - Add stems export toggle and bus metadata structure for artifacts (bus_id, roles, gain_db).  
- Render planner/service (audio_render/planner.py, service.py)  
  - Map automation/fades into ffmpeg filter graph deterministically; ensure track/clip ordering stable; add headroom gain staging and optional dither.  
  - Add export presets (podcast/music/voiceover/draft) with limiter thresholds, loudness targets (LUFS), headroom, dither; record in plan meta.  
  - Register master (`audio_render`) and stems (`audio_bus_stem`) artifacts with meta (bus_id/roles/export_preset/limiter/headroom/loudnorm_target/dithered).  
  - Avoid duplicate registrations; ensure media_v2 keys and meta are consistent.  
- Arrangement/structure integration (if needed)  
  - Propagate markers/roles from arrangement/structure engines to timeline tracks for bus routing; validate role mapping; clamp overlapping automation.  
- Validation & safety  
  - Validate conflicting automation keyframes, fade ranges, unknown export preset; clear errors (no silent skips).  
  - Keep HTTP signatures stable; mark CONTRACT CHANGE if models change and update only in-lane callsites.  
- Docs sync  
  - Update preset tables (mix/export), automation fields, stem schema in this doc and ENGINE_INVENTORY if meta changes.  
- Determinism  
  - Ensure plan strings and artifact meta are deterministic for identical inputs; record render_profile/export_preset in meta.

5. Tests  
- engines/audio_timeline/tests/test_timeline.py: automation/fade persistence and validation (bounds, ordering, sum of fades).  
- engines/audio_render/tests/test_a04_mix.py: automation application, fade/crossfade curves, export preset gain staging/loudness/dither, deterministic plan strings.  
- engines/audio_render/tests/test_render_stems.py: stems export with bus mapping/meta; ensures artifacts carry bus_id/roles/export_preset.  
- engines/audio_mix_buses/tests/test_buses.py: role-to-bus mapping, preset coverage, stems toggle behavior.  
- engines/audio_arrangement_engine/tests/test_arrangement.py (if touched): role propagation into timeline.  
- engines/audio_structure_engine/tests/test_structure.py (if touched): marker/role handling compatibility.  
Additional required cases:  
- Negative tests for invalid automation (overlapping times), fade sums exceeding duration, unknown export preset.  
- Determinism: identical timeline -> identical plan/meta.  
- CONTRACT CHANGE tests if models/artifacts change.

6. Docs & examples  
- Update this phase doc with mix/export preset table, automation fields, stem schema, and sample plan meta.  
- Update audio_program overview with example plan snippets.  
- Add example: POST timeline with two tracks (dialogue/music) + automation/fades → render mix (podcast preset) + stems; show artifact meta for master and stems.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If you need a new artifact kind or model field, mark CONTRACT CHANGE in this doc and only update explicitly listed files/tests.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; no TODOs unless a blocking external dependency is documented.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if something outside seems required, stop and report. Deliver full Definition of Done with passing tests. After finishing, proceed to the next domain unless blocked by TODO – HUMAN DECISION REQUIRED.

9. Runtime notes & contracts

**Timeline automation & fades**
- `AudioClip` exposes `gain_db`, `pan`, `fade_in_ms`, `fade_out_ms`, `crossfade_in_ms`, `crossfade_out_ms`, and `automation` maps so keyframes can live on the timeline. The service clamps fades/crossfades to fall within the clip duration, rejects negatives, and enforces automation keyframe order/uniqueness via `_validate_clip_automation` (duplicate times or points outside the clip window raise `ValueError`). Track-level automation is sorted deterministically and also rejects duplicates to keep rendered gains stable.

**Mix buses & stems metadata**
- `MixGraph` presets (currently `default_mix`) route track roles like `vox`, `drums`, `bass`, `keys`, `fx`, and `ambience` into dedicated buses with role-aware gain defaults. `build_ffmpeg_mix_plan` now emits deterministic bus metadata for each output: `bus_id`, `roles`, `gain_db`, `export_preset`, limiter/headroom/loudnorm targets, and `dithered` flags. Stems exports can be toggled per request (`RenderRequest.stems_export`), and `audio_bus_stem` artifacts include the bus metadata plus the parent master asset link.

**Export presets & determinism**
- Export presets (`default`, `podcast`, `music`, `voiceover`) define limiter thresholds, headroom, loudness targets, and dither. Unknown presets now raise `ValueError("Unknown export preset: ...")` so callers can't silently fallback to defaults; deterministic filter graphs (fades → automation → bus mixing → headroom → loudnorm → limiter → dither) ensure identical timelines yield identical plans, and plan metadata records the preset used along with `master`/`stem` bus IDs.

**Example workflow**
1. A worker builds a timeline with two tracks: a dialogue track (`role="vox"`, `gain` automation) and a music track (`role="music"`, `fade_in_ms=200`).  
2. `AudioRenderService` sees `RenderRequest(export_preset="podcast", stems_export=True)` and `mix_preset_id="default_mix"`, calls `build_ffmpeg_mix_plan`, and writes a deterministic ffmpeg filter graph plus bus metadata.  
3. The master artifact metadata contains `{bus_id:"master", roles:["master"], export_preset:"podcast", limiter_thresh:-1.0, loudnorm_target:-16.0, dithered:true}` while each stem artifact keeps its bus info (`bus_drums`, `bus_music`, etc.) so downstream automation or UI can align stems back to their roles.  
4. Future renders of the same sequence + preset reuse the same `filter_complex` string, ensuring the exported master/stems play identically.
