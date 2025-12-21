Media Muscle Program – Lane A (Video, Audio, Image/Vector)

This lane hardens video and audio muscle to production-ish (P3-) and stands up the first serious image/vector stack. Run phases in order; each phase has its own doc with concrete steps.

Video Muscle – Final Pass
- PHASE_V01: Real detectors + artifacts (regions, visual meta, captions, anonymise)
- PHASE_V02: Effects, transitions, stabilise/slowmo quality, filter/preset expansion
- PHASE_V03: Render/preview hardening (GPU profiles, proxies, chunk jobs, errors)
- PHASE_V04: Multicam + assist polish (alignment, auto-cut, highlights, focus)
  - Detailed execution for each phase lives in the corresponding PHASE_V0x docs; follow them sequentially.

Audio Muscle – Final Pass
- PHASE_A01: Backend hardening (ffmpeg/librosa/demucs/install, error handling)
- PHASE_A02: Semantic stack upgrade (ASR/VAD/beats, caching, slicing)
- PHASE_A03: Creative tools (FX/macro expansion, groove quality, time/pitch QA)
- PHASE_A04: DAW-ish timeline/mix (automation, fades, bus/stems, exports)
  - Detailed execution for each phase lives in the corresponding PHASE_A0x docs; follow them sequentially.

Image & Vector Muscle – First Pass
- PHASE_I01: Image layer core (layers, blend modes, filters, render/export)
- PHASE_I02: Selections/masks/adjustments and video interoperability
- PHASE_I03: Typography/variable fonts layout engine
- PHASE_I04: Vector primitives + path ops + SVG I/O
- PHASE_I05: Integration & presets (export profiles, media_v2 artifacts)
  - PHASE_I03 covers typography/variable fonts; PHASE_I04 covers vector primitives; both feed into image_core/video_text. Follow PHASE_I0x docs sequentially.

Execution note: Future coding agents should complete each phase (code + tests + docs) then immediately continue to the next phase unless a phase marks TODO – HUMAN DECISION REQUIRED and cannot proceed with defaults.
