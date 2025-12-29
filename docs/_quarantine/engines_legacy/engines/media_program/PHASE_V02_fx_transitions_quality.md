1. Goal  
Expand effects/transition library, improve stabilise/slowmo quality, and ensure presets cover common edits with deterministic ffmpeg graphs for CapCut-lite timelines.

North star + Definition of Done  
- North star slice: CapCut-lite transitions/filters/slowmo/stabilise on 2–3 track edits (A-roll, B-roll, overlay) at YouTube/TikTok quality.  
- Definition of Done:  
  - Transition/filter catalog covers core CapCut-lite moves with deterministic graphs (mask-aware where relevant).  
  - Slowmo/stabilise presets produce predictable results with fallbacks; plan meta records methods.  
  - Presets library (filters/motion/text) ready for UI reuse; profiles updated with audio params.  
  - Tests validate ordering, param validation, mask handling, and fallbacks; docs list catalogs and examples.

2. Scope (In / Out)  
- In: video_render filter chain/profiles, video_presets catalog, video_text styling hooks, slowmo/stabilise quality settings, transition mapping.  
- Out: detectors, auth/tenant/safety, UI, new product surfaces.

3. Modules to touch  
- engines/video_render/service.py  
- engines/video_render/planner.py  
- engines/video_render/profiles.py  
- engines/video_render/tests/test_render_filters_transitions.py  
- engines/video_render/tests/test_render_slowmo.py  
- engines/video_render/tests/test_render_stabilise.py  
- engines/video_render/tests/test_v02_fx.py  
- engines/video_presets/service.py  
- engines/video_presets/routes.py  
- engines/video_presets/tests/test_presets_endpoints.py  
- engines/video_text/service.py (only if preset metadata needs updating)  
- engines/video_text/tests/test_video_text_service.py (only if service changes)  
- engines/video_slowmo/backend.py  
- engines/video_stabilise/service.py  
- engines/video_stabilise/backend.py  
- docs/engines/media_program/PHASE_V02_fx_transitions_quality.md  
- docs/engines/video_audio_atomic_design.md (examples only)  
- READ-ONLY context: other engine files not listed.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Design & catalogs  
  - Define transition catalog (crossfade, dip_to_black/white, wipe_left/right, push_left/right, slide_up/down) mapped to ffmpeg `xfade` aliases + `acrossfade` for audio; record meta (type, order, start_ms, duration_ms, alias).  
  - Define filter catalog additions (sharpen, vignette, hue_shift, film_grain, bloom, gamma, levels, LUT slot) with parameter clamps and ffmpeg expressions; ensure mask-aware path via alphamerge.  
  - Update profiles.py with explicit profiles (draft_480p_fast, preview_720p, social_1080p_h264, master_4k_prores) including audio codec/bitrate/threading; note GPU/CPU compatibility.  
  - Define slowmo quality presets (high/medium/fast) and stabilise defaults (smoothing/zoom/crop/tripod) with metadata fields.  
- Implementation (video_render/service.py, planner.py, profiles.py)  
  - Map transitions to `xfade`/`acrossfade` with duration clamping; ensure deterministic ordering in plan builder.  
  - Add filter handlers for new catalog entries with param validation/clamps; support mask-aware application (alphamerge) when target has mask.  
  - Integrate slowmo presets: choose optical-flow options for high/medium, `tblend` fallback for fast or missing flow; record `meta.slowmo_details` per clip.  
  - Integrate stabilise defaults; surface `meta.stabilise_warnings` when transforms missing; ensure plan uses transform artifact if present.  
  - Update render profiles to include audio settings, threading; ensure backward compatibility; include profile label in plan meta.  
  - Validate inputs: reject unknown filter/transition types; clamp out-of-range params; ensure blend mode + speed adjustments co-exist deterministically.  
- Presets (video_presets/service.py, routes.py)  
  - Add style presets (cinematic, vlog, punchy, monochrome) and motion presets; include IDs, params, and tags; expose via routes.  
  - Optionally add per-profile default preset references.  
- Text styling (video_text/service.py)  
  - If presets reference text styles, ensure service can surface preset metadata; keep backward compatibility.  
- Slowmo/stabilise backends  
  - In video_slowmo/backend.py, expose quality presets and ensure deterministic defaults; handle missing deps with clear error.  
  - In video_stabilise/backend.py/service.py, set deterministic defaults; add warnings when transform artifacts missing.  
- Docs sync  
  - Add catalog tables and examples to this doc and video_audio_atomic_design.md.  
- Validation & safety  
  - Reject missing tenant/env if touched; preserve existing auth model (none added).  
  - No prod fallback to temp paths; follow existing storage patterns.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

5. Tests  
- engines/video_render/tests/test_render_filters_transitions.py: ordering of transitions, mask-aware graphs, param validation errors.  
- engines/video_render/tests/test_render_slowmo.py: quality presets (high/medium/fast), fallback when optical flow unavailable, meta assertions.  
- engines/video_render/tests/test_render_stabilise.py: defaults applied, warning when transform missing, uses transform when present.  
- engines/video_render/tests/test_v02_fx.py: mapping of new filters to expected ffmpeg args; LUT handling if applicable.  
- engines/video_presets/tests/test_presets_endpoints.py: new presets exist with correct params/meta; routes return them.  
- engines/video_text/tests/test_video_text_service.py: preset metadata passthrough if text presets added.  
Additional required cases:  
- Fixture-based regression combining speed + transitions + filters yields deterministic plan string.  
- Negative tests for unknown filter/transition -> clear ValueError.  
- Profile selection includes audio settings and records in plan meta.

6. Docs & examples  
- Update this phase doc with catalog tables (filters, transitions, presets) and slowmo/stabilise presets.  
- Update video_audio_atomic_design.md with example graphs and profile table.  
- Provide example: two-clip timeline with crossfade + vignette + slowmo (medium) → expected ffmpeg graph snippet and plan meta.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If you need a new artifact kind or model field, you must mark CONTRACT CHANGE in this doc, and only update the specific media_v2 / model files and tests explicitly listed in Modules to touch (none expected here).  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; no TODOs unless a blocking external dependency is documented.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if you think another file is needed, stop and report instead of editing it. Within the allow-list, deliver full Definition of Done with passing tests. When done, proceed directly to PHASE_V03 unless a TODO – HUMAN DECISION REQUIRED truly blocks you.

9. Transitions catalog  
| Transition | FFmpeg `xfade` alias | Audio alias | Notes |
| --- | --- | --- | --- |
| `crossfade` | `fade` | `acrossfade` | Standard dissolve across video/audio. |
| `dip_to_black` | `fadeblack` | `acrossfade` | Fade out/in to black with smooth audio handoff. |
| `dip_to_white` | `fadewhite` | `acrossfade` | Fade through white before the next clip. |
| `wipe_left` | `wipeleft` | `acrossfade` | Horizontal wipe from the right edge. |
| `wipe_right` | `wiperight` | `acrossfade` | Horizontal wipe from the left edge. |
| `push_left` | `slideleft` | `acrossfade` | Pushes the incoming clip from right to left. |
| `push_right` | `slideright` | `acrossfade` | Pushes the incoming clip from left to right. |
| `slide_up` | `slideup` | `acrossfade` | Vertical push from bottom to top. |
| `slide_down` | `slidedown` | `acrossfade` | Vertical push from top to bottom. |
> The planner sorts transitions by `start_ms` + `id`, clamps durations to the shorter clip, and reports both `video_alias` and `audio_alias` in `meta.transitions` so downstream automation can inspect which FFmpeg alias powered each cut.

10. Filter catalog & masks  
| Filter | Description | Parameter clamps / defaults | Mask awareness |
| --- | --- | --- | --- |
| `sharpen` | Boosts detail via `unsharp`. | `luma_x/y` 1–20, `luma_amount` 0–5 (default 0.5). | No mask (global). |
| `vignette` | Soft spotlight around frame edges. | `angle` 0–1, `softness` 0.1–1, `strength` 0.1–1. | No mask. |
| `hue_shift` | Rotates hue wheel. | `shift` -180..180°. | No mask. |
| `film_grain` | Adds noise for texture. | `strength` 0–50. | No mask. |
| `gamma` | Linear gamma ramp. | `gamma` 0.1–6. | No mask. |
| `bloom` | Gentle glow via `boxblur`. | `intensity` 0–1, `radius` 2–60 (defaults 10). | No mask. |
| `levels` | Combines brightness/contrast/gamma tweaks. | `black` 0–0.5, `white` 0.5–1, `gamma` 0.1–6. | No mask. |
| `teeth_whiten` | Brightens and contrasts teeth. | `intensity` 0–1 (maps to brightness/contrast). | Region-aware / clip masks. |
| `skin_smooth` | Gaussian blur for skin areas. | `intensity` 0–1 (sigma up to 5). | Region-aware / clip masks. |
| `eye_enhance` | Slight contrast + brightness boost. | `intensity` 0–1. | Region-aware / clip masks. |
| `face_blur` | Strong blur for anonymisation. | `strength` 0.1–1 (Luma radius up to 50). | Region-aware / clip masks. |
| `lut` | Applies a 3D LUT via path or artifact. | `lut_path` or `lut_artifact_id` required. | Applies globally unless a mask is attached. |
> `video_render` generates expressions via `_build_filter_expression`, validates parameter ranges, and routes region-aware filters through `resolve_region_masks_for_clip`. When a clip mask or region mask exists the engine splits the stream, applies the filter, then `alphamerge`s the masked result back with `overlay`, keeping the rest of the clip untouched.

11. Slowmo & stabilise presets  
- **Slowmo** — `slowmo_details` metadata lists `{clip_id, quality, method, mode, mc_mode, me_mode, fps, preset_description}` so planners/motion presets know whether `minterpolate` (high/medium) or `tblend` (fast/missing optical flow) produced the slowmo. Quality presets are recorded as `high` / `medium` / `fast` and include GPU/CPU-friendly defaults plus the textual `description` recorded in the metadata for audit.
- **Stabilise** — `stabilise_details` records `{clip_id, smoothing, zoom, crop, tripod, description, backend}` while `stabilise_warnings` captures missing transform artifacts so automation can fall back gracefully. Defaults (15 smoothing, 1x zoom, no crop, tripod=1) are enforced from `STABILISE_DEFAULTS`, and transforms append to the filter graph before slowmo or filters run.
- Plan meta now carries `render_profile_description` describing the active profile (e.g., “1080p H.264 for social delivery with balanced quality”) alongside `transitions`, `slowmo_details`, and `dependency_notices`. `dependency_notices` now reports each `video_region_summary`, `visual_meta`, or `captions` artifact with its `backend_version` + `cache_key`, enabling dry-run auditing and deterministic caching.

12. Example timeline (two-clip crossfade + vignette + medium slowmo)  
1. Clip A (A-roll) + Clip B (B-roll), each 1s long, overlapping with `crossfade` 500ms.  
2. Clip A carries a `vignette` filter and Clip B requests `slowmo_quality=medium` with `optical_flow=True`.  
3. Planner emits filters: `[0:v]...vignette...xfade=transition=fade:duration=0.500:offset=0`, the slowmo chain `minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bilin`, and audio `acrossfade=d=0.500`.  
4. Plan meta reflects `render_profile_description`, `transitions[0].video_alias == "fade"`, `slowmo_details[0].method == "minterpolate"` plus the `preset_description`, and there are mask-aware dependencies highlighted in `dependency_notices`.  
5. Dry runs surface `warnings` when assets missing (e.g., `video_regions missing for asset ...`), keeping the CapCut-lite guardrails intact.
