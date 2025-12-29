# Engine Marketing Cheat Sheet

Fast orientation for GTM/Control Tower on what each engine does and how to position it (non-dev phrasing). Derived from ENGINE_INVENTORY; statuses mirror prod-grade/prod-lite/stub.

## Video Engines
- **video_render** — One-click video finishing: stitches timelines, applies looks/filters, and outputs shareable renders. Status: production-ready.
- **video_timeline** — Collaborative video storyboard: projects, sequences, tracks, clips, and effects in one structured timeline store. Status: production-ready.
- **video_multicam** — Multi-camera assembler: syncs angles and builds a cut you can refine. Status: prod-lite (alignment is basic).
- **video_mask** — Mask manager: uploads and attaches masks for selective edits/overlays. Status: prod-lite.
- **video_regions** — Smart regions finder: auto-detects objects/areas for targeted edits. Status: prod-lite (detection stubbed).
- **video_visual_meta** — Visual insights: pulls palette/faces/meta for quick styling or compliance checks. Status: prod-lite.
- **video_text** — Styled titles/overlays: generates branded text treatments for videos. Status: prod-lite.
- **video_presets** — Render & timeline presets: reusable looks and export profiles. Status: prod-lite.
- **video_anonymise** — Face/PII blurring pipeline. Status: prototype (needs real detector).
- **video_360** — 360/VR prep: handles projection flags and transforms. Status: prod-lite.
- **video_frame_grab** — Frame grabber CLI: pulls stills from video. Status: prototype (CLI only).
- **origin_snippets** — “Trace back to source” clips: turns audio hits/loops into video snippets and renders with provenance. Status: prod-lite.
- **page_content** — Web page fetch & clean: pulls readable text from URLs for downstream use. Status: prod-lite.

## Audio Engines
- **audio_service** — End-to-end audio pipeline hub: ASR, diarization, voice tasks with caching. Status: production-ready.
- **audio_semantic_timeline** — Audio understanding: labels moments (speech/music/etc.) for quick navigation. Status: production-ready.
- **audio_voice_enhance** — Dialog cleaner: boosts clarity and removes noise with caching. Status: production-ready.
- **audio_sample_library** — Sample crate manager: CRUD/tag/search of audio samples. Status: prod-lite.
- **audio_field_to_samples** — Field-to-snippet cutter: slices long captures into usable bites. Status: production-ready (library).
- **audio_hits** — Beat/hit detector: finds onsets and saves slices. Status: prod-lite (backend may be stub).
- **audio_loops** — Loop finder: detects repeating bars/loops and saves slices. Status: prod-lite.
- **audio_voice_phrases** — Voice phrase manager: stores detected phrases. Status: prod-lite (no endpoint).
- **audio_core + audio CLI engines (asr_whisper, beat_features, ingest_*, preprocess_basic_clean, segment_ffmpeg)** — Utility runners for ingest, segmentation, ASR, and feature prep. Status: prototypes/ops utilities (CLI only).
- **align (audio_text_bars)** — Stub offset/align helper. Status: prototype.

## 3D / Scene Engines
- **scene_engine** — Scene builder: turns JSON layouts into 3D scenes with recipes and editors. Status: prod-lite (tested).
- **animation_kernel** — Procedural animation sandbox: auto-rig + simple IK/walk cycles. Status: prototype.
- **mesh_kernel / material_kernel / solid_kernel / stage_kernel** — Geometry and material toolkits: primitives, mesh ops, stages. Status: prod-lite (library-only).

## Control / Safety / Routing / Policy
- **rootsmanuva_engine + routing** — Deterministic router: scores choices for which agent/model/tool to run. Status: prod-lite (service-level, no HTTP).
- **strategy_lock** — Human-in-loop gate: enforces checkpoints before publish/actions. Status: prod-lite (HTTP).
- **three_wise** — Triple-check safety reviewer (stubbed). Status: prod-lite.
- **firearms** — Policy/license guardrail adapter. Status: prod-lite.
- **kill_switch** — Emergency stop flags per tenant/global. Status: prod-lite.
- **temperature** — Control “risk/energy” dials per surface/app. Status: prod-lite.
- **budget** — Usage/cost tracker with summaries. Status: prod-lite.
- **billing** — Billing metadata/Stripe stub. Status: prototype.
- **kpi** — KPI corridor config service. Status: prod-lite.
- **forecast** — Forecast stubs for costs/KPIs. Status: prod-lite (no HTTP).
- **eval** — Evaluation scaffolding for agents/models. Status: prod-lite (library).
- **creative** — Creative intent helper (colors/fonts/layout cues). Status: prod-lite (library).
- **analytics_events** — Event logger for product analytics. Status: prod-lite.
- **seo** — SEO keyword/meta helper (stub). Status: prototype.
- **guardrails / safety / security** — Safety/privacy/crypto utilities; library-only. Status: prod-lite.
- **logging/events** — Event logging with PII stripping. Status: prod-lite (library).
- **orchestration** — Agent orchestration patterns. Status: prod-lite (library).
- **privacy** — Privacy filters/helpers. Status: prod-lite (library).
- **bossman** — Ops dashboard API for state-of-world summaries. Status: prod-lite.

## Data / Memory / Storage / Nexus
- **media_v2** — Canonical media catalog for assets/artifacts with upload/probing. Status: production-ready.
- **media (v1)** — Legacy media service. Status: prod-lite.
- **memory** — Episode/chat memory store. Status: prod-lite.
- **maybes** — Scratchpad/notes with tags/pin. Status: prod-lite.
- **nexus (atoms, cards, index, packs, raw_storage, settings, vector_explorer)** — Vector/RAG/data plane: upload raw data, index/search vectors, manage atoms/cards/packs/settings. Status: prod-lite (dev-facing).
- **page_content** — (see Video) web text fetcher; also useful as data ingest.

## Dataset/Tag/Train Utilities (CLI/spec)
- **dataset/pack_jsonl** — Packs datasets for training. Status: prototype (CLI).
- **tag/flow_auto** — Auto-tagging flow script for content prep. Status: prototype (CLI).
- **text cleaners (clean_asr_punct_case, normalise_slang)** — ASR text cleanup utilities. Status: prototypes (CLI).
- **train (lora_peft_hf, lora_local)** — LoRA training scripts. Status: prototypes (CLI).

## Enterprise Safety Locking & Controls
- **Strategy Lock (HITL gate)** — Enforces human checkpoints before high-impact actions (publish/execute), designed to block autonomy until approvals land. Status: prod-lite.
- **Firearms (policy/licensing guardrail)** — Central policy verdicts for tools/actions; acts as allow/deny/license check; built for enterprise governance. Status: prod-lite.
- **Kill Switch (global/tenant stop)** — Emergency stop flags that can halt flows per tenant or globally. Status: prod-lite.
- **Budget / KPI / Temperature Corridors** — Safety rails on spend/perf/risk: budgets and KPI corridors feed temperature controls to slow/stop or uplift activity. Status: prod-lite.
- **Guardrails / Safety Adapters** — PII/guardrail utilities to filter/deny unsafe content; plugs into Firearms outcomes. Status: prod-lite.
- **Logging / Audit (logging.events)** — Event log with PII stripping for auditability; foundation for enterprise audit trails. Status: prod-lite.
- **Three Wise (triage safety reviewer)** — Stubbed triple-check reviewer to require consensus before risky steps. Status: prod-lite.
- **Memory / Maybes (controlled scratchpads)** — Tenant-scoped note/memory stores to keep state without leaking across tenants. Status: prod-lite.
- **Security (sign/verify)** — Crypto helpers to protect payload integrity. Status: prod-lite.

### Quick positioning notes
- Production-ready: ready for frontend/agent use with tenant/env context — video_render, video_timeline, media_v2, audio_service, audio_semantic_timeline, audio_voice_enhance, audio_field_to_samples, (legacy media).
- Prod-lite: works today with tests but needs auth/persistence/backends hardened — most HTTP services above.
- Prototype/stub: CLI utilities and DSP stubs — alignment, anonymise, billing, seo, frame_grab, animation_kernel, ingest/ASR runners.
