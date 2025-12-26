# PHASE_I_COMFORT_social_thumbnails

## 1. North star + Definition of Done  
- North star: “CapCut/Photoshop-comfort” social image stack—able to generate YouTube/IG/TikTok thumbnails using engine primitives only (image_core, typography_core) with deterministic artifacts and tests; supports YouTube 16:9, vertical 9:16 stories, square 1:1, and 4:3 comfort presets.  
- Definition of Done:  
  - Social image presets defined: `youtube_thumb_16_9` (1280x720), `social_vertical_story_9_16` (1080x1920), `social_square_1_1` (1080x1080), `social_4_3_comfort` (1440x1080), each with safe_title_box defaults (width 90% / height 80% of canvas, centered; 5% horizontal margins, 10% vertical margins).  
  - Subject cutout primitive (person/face mask) available; outputs mask artifact and can be applied as foreground layer mask.  
  - Layer adjustment presets: background “drama” (darken/blur/B&W option), subject “pop” (brightness/contrast), B&W background with color subject; color overlay/outer glow/stroke-like effects for text layers.  
  - Typography presets for large headline with glow/overlay; default headline style uses text color #FFFFFF, overlay #FFFFFF @90% opacity, outer glow #FFFFFF @75% opacity with radius = 0.03 * min(width, height) (resolution-scaled, e.g., ~24px at 1280x720); reusable styles, not hard-coded to one recipe.  
  - “No-Code-Man recipe” defined: input frame/photo + title + preset → cutout → background adjust → foreground adjust → text layer with preset style → optional extend canvas primitive (mirror/blur) → output composition artifact with meta (preset_id, recipe_id, subject_mask_id).  
  - Minimal extend-canvas primitive implemented (simple mirror/blur), with documented “future: generative fill” hook; deterministic outputs for same inputs.  
  - Tests cover presets, cutout application, layer presets, typography styles, and recipe flow; docs include example flows.

## 2. Scope (In / Out)  
- In: image_core, typography_core, any existing image preset/recipe docs, HTTP surfaces in those engines; docs under docs/engines/image_program.  
- Out: auth/tenant/core/orchestration/connectors/UI; no generative model implementation (stub/hook allowed); no video engine changes.

## 3. Hard allow-list (modules/docs)  
- engines/image_core/models.py  
- engines/image_core/service.py  
- engines/image_core/routes.py  
- engines/image_core/auto_crop.py  
- engines/image_core/tests/test_social_presets.py  
- engines/image_core/tests/test_subject_cutout.py  
- engines/image_core/tests/test_recipe_no_code_thumb.py  
- engines/typography_core/models.py  
- engines/typography_core/service.py  
- engines/typography_core/tests/test_thumbnail_text_styles.py  
- docs/engines/image_program/PHASE_I_COMFORT_social_thumbnails.md  
- docs/engines/image_program/IMAGE_THUMBNAIL_TODOS.md  
> STOP RULE: If you believe any file outside this list must be changed, stop and return a report instead of editing it.

## 4. Mechanical implementation checklist  
- Social presets: add preset definitions (IDs, width/height, aspect, optional safe-title box) and ensure render/export honors them.  
  - Subject cutout primitive: real detector-backed mask (person/face); produce mask artifact; apply as foreground mask in compositions; if detector/backend missing, fail with clear error (no stub/full-frame fallback).  
- Layer adjustments: implement presets for background drama (darken/blur/B&W), subject pop (brightness/contrast), B&W background/color subject toggle, color overlay/outer glow/stroke-like effects for text layers.  
  - Typography presets: big headline style with glow/overlay defaults (#FFFFFF text/overlay, overlay 90% opacity; outer glow #FFFFFF 75% opacity, radius=0.03*min(w,h)) and color swap; reusable via typography_core.  
- Recipe (“No-Code-Man”): define pipeline steps using existing ops—cutout → background adjust → foreground adjust → text layer with preset style → optional extend-canvas (mirror/blur) → output composition artifact with meta (preset_id, recipe_id, subject_mask_id).  
- Extend-canvas primitive: mirror/blur edges to expand canvas; document future hook for generative fill (no implementation).  
- Keep all behavior inside allow-list; if more is needed, STOP.

## 5. Tests  
- engines/image_core/tests/test_social_presets.py: presets exist, correct dimensions/aspect, safe-title box if provided.  
- engines/image_core/tests/test_subject_cutout.py: mask produced/applied; fallback behavior when detector missing.  
- engines/image_core/tests/test_recipe_no_code_thumb.py: full recipe yields deterministic composition/meta; background/foreground/text adjustments applied.  
- engines/typography_core/tests/test_thumbnail_text_styles.py: typography presets produce expected style fields (glow/overlay/size).  
Commands:  
- `python3 -m pytest engines/image_core/tests/test_social_presets.py`  
- `python3 -m pytest engines/image_core/tests/test_subject_cutout.py`  
- `python3 -m pytest engines/image_core/tests/test_recipe_no_code_thumb.py`  
- `python3 -m pytest engines/typography_core/tests/test_thumbnail_text_styles.py`

## 6. Docs & examples  
- Examples:  
  - “Make a YouTube thumbnail from frame X with title ‘NO.CODE.MAN’” showing preset selection, cutout, background drama, subject pop, headline with glow.  
  - “Generate IG story cover from portrait photo with B&W background and color subject.”  
  - Note how outputs can feed future apps (CAIDENCE) and generic editor flows.  

## 7. HTTP surfaces
- `GET /image/social-thumbnails` returns the COMFORT presets (`youtube_thumb_16_9`, `social_vertical_story_9_16`, `social_square_1_1`, `social_4_3_comfort`) along with the safe-title box defaults, aspect, format, and recipe_id.
- `POST /image/social-thumbnails/recipe` materializes the No-Code-Man recipe end-to-end: it requires `tenant_id`, `env`, `asset_id`, `preset_id`, and `title`, accepts `extend_canvas`, `bw_background`, and `canvas_extension_mode` (mirror_blur vs. generative_fill) flags, and either fails with a clear `400` when the detector can't find a subject or returns an `image_render` artifact whose meta contains `preset_id`, `recipe_id`, `subject_mask_id`, and the scaled safe-title box.

### Example: YouTube thumb from frame  
1. Call `POST /image/social-thumbnails/recipe` with the tenant/env headers plus `{ "asset_id": "...frame...", "preset_id": "youtube_thumb_16_9", "title": "NO.CODE.MAN" }`.  
2. The service runs the Haar-based subject detector, captures the mask artifact, applies the background drama adjustments (darken, blur, B&W) to the base layer, layers the masked foreground with the subject pop adjustment, and places the headline text asset generated by typography_core (white text + 90% overlay + outer glow radius = 0.03×min) inside the 90% × 80% safe box.  
3. The response returns `artifact_id`, the matching metadata, and the mask id—clients can show the mask or reuse it for future edits without re-detecting.  

### Example: IG story cover with B&W background and color subject  
1. POST the same recipe endpoint but set `"preset_id": "social_vertical_story_9_16"`, `"bw_background": true`, and optionally `"extend_canvas": true` with `"canvas_extension_mode": "generative_fill"` once a provider is configured; this lets the mirror/blur or future generative fill hook pad the full-height story frame while keeping the background monochrome and the subject pop adjustments intact, and the text stays inside the centered safe box (5% / 10% margins).  
2. The generated artifact meta confirms the final width/height, safe title box, recipe_id, and the subject mask artifact so downstream editors or CAIDENCE consumers can layer more content deterministically.  
   - The extend-canvas patch is currently a mirror + blur pad; once a generative fill provider is wired in (`canvas_extension_mode: "generative_fill"`), it can replace the mirrored edges deterministically.

## 7. Guardrails  
- No new auth/tenant logic; keep existing tenant/env/request_id meta patterns.  
- No connectors, logging, orchestration, or UI work.  
- Do not touch video engines.  
- Stay within allow-list; STOP on any expansion; mark CONTRACT CHANGE if any public schema changes.

## 8. Execution note  
This phase is docs + plan only; intended for GPT-5.1 Codex Mini/Gemini-class worker agents to implement in small, independent T0x tasks. Workers must implement code+tests+docs strictly within the allow-list to reach DoD; STOP and report if additional files seem necessary.
