# NorthStar Engines · Inventory and Audio/Video Overview

## Engine inventory
- **Chat transports** — `engines/chat/service` — In-memory chat threads/messages with HTTP/WS/SSE transports for front-end work. Endpoints: `GET/POST /chat/threads`, `GET/POST /chat/threads/{id}/messages`, `/ws/chat/{id}`, `/sse/chat/{id}` (`engines/chat/service/http_transport.py`, `ws_transport.py`, `sse_transport.py`). Models: `Contact`, `Message`, `ChatScope` (`engines/chat/contracts.py`), runtime-configured tenant/env for logging.
- **Media ingest** — `engines/media/service/routes.py` — FastAPI router mounted in chat app for raw media uploads and listing. Endpoints: `POST /media/upload`, `GET /media/stack`. Entities: `GcsClient` uploads to `tenant/media/...`, `NexusDocument` stored via backend, `DatasetEvent` log.
- **Vector Explorer** — `engines/nexus/vector_explorer` — FastAPI routers for ingesting and querying vector corpora. Endpoints: `POST /vector-explorer/ingest` and `GET /vector-explorer/scene`. Entities: `VectorExplorerQuery/Item` (`schemas.py`), Firestore corpus repo, Vertex vector store + embeddings, optional GCS for binaries.
- **BBK local service** — `engines/bot-better-know/service` — FastAPI wrapper around local audio pipeline/training. Endpoints: `GET /health`, `POST /bbk/upload-and-process`, `POST /bbk/start-training`. Entities: run/work dirs under `engines/bot-better-know/data`, uses `audio_core` pipeline outputs and `lora_train`.
- **Scene Engine** — `engines/scene_engine/service` — FastAPI service to map abstract grids/boxes to scene JSON. Endpoints: `GET /health`, `POST /scene/build`. Entities: `SceneBuildRequest`, `Scene` (`core/types.py`), mapping/recipes in `core/`.
- **Maybes scratchpad** — `engines/maybes` — FastAPI router for personal “maybe” items. Endpoints under `/maybes`: create/list/update/archive. Entities: `MaybeItem` with tenant/env/user ownership; Firestore or in-memory repo.
- **Vector/Nexus core** — `engines/nexus` — Backends for Firestore persistence (`backends/firestore_backend.py`), embeddings (`embedding.py`), vector store abstractions (`vector_store.py`), schemas for snippets/events/usage (`schemas.py`).
- **Audio atomic engines** — `engines/audio` — CLI/runner style engines: ingest (local dir/file, remote pull), preprocessing, segmentation, beat analysis, Whisper ASR stub. No HTTP endpoints; each has `runner.py`. Entities: Pydantic `Input/Output` types per engine and `SegmentMetadata`/`BeatMetadata`.
- **Audio core pipeline** — `engines/audio_core` — Local pipeline runner chaining clean → beats → ASR (faster-whisper if installed) → JSONL dataset + optional LoRA stub. Entrypoint: `run_pipeline` (`runner.py`), helpers `asr_backend.py`, `dataset_builder.py`, `lora_train.py`.
- **Alignment** — `engines/align/audio_text_bars` — Simplified bar aligner turning ASR payloads into bar entries; runner only. Entities: `BarEntry`, `AlignAudioTextBarsInput`.
- **Text cleaners** — `engines/text/normalise_slang`, `engines/text/clean_asr_punct_case` — CLI-style engines to normalize slang and add punctuation/casing to ASR text. Entities: payload lists of ASR segments/strings.
- **Tagging** — `engines/tag/flow_auto` — Heuristic flow tagging over bar lists; runner only. Entities: `FlowPair`, bar dicts with bpm/syllables.
- **Dataset packing** — `engines/dataset/pack_jsonl` — Packs bar files into train/val JSONL; runner only. Entities: `PackJsonlInput/Output`.
- **Training** — `engines/train/lora_local` (metadata stub) and `engines/train/lora_peft_hf` (PEFT stub). Entrypoint: `run(config)` writing metadata/adapter placeholders.
- **Video frame grab** — `engines/video/frame_grab` — ffmpeg-based still extraction with CLI runner. Entities: `FrameGrabInput/Output`, `FrameGrabResult`.
- **Bot Better Know pipeline** — `engines/bot-better-know/pipeline` — Real grime audio pipeline scripts (ffmpeg segmentation, faster-whisper ASR with word timings, slang normalization, beat features, bar alignment, flow tagging, JSONL packing, LoRA training) orchestrated by `pipeline/ingest.py`. CLI scripts, GCS-heavy.
- **Guardrails/Safety/Security** — `engines/guardrails/*` (PII text scanner, strategy lock, three-wise check), `engines/safety/adapter.py`, `engines/security/ingestor.py` — library-style engines for safety decisions, no HTTP.
- **Routing/Rootsmanuva** — `engines/rootsmanuva_engine/service.py` plus schemas in `engines/routing` — model selection scoring engine, no HTTP wrapper present.
- **Control/Temperature** — `engines/control/temperature` — banding engine for KPI corridors; runner/tests only.
- **Logging** — `engines/logging/events/engine.py` — strips PII then writes `DatasetEvent` to Nexus backend (Firestore).
- **Budget/Eval/Forecast/Creative/SEO/Storage/Design** — smaller utility engines/services used by other systems; no direct audio/video relevance. Storage provides `GcsClient` for media/dataset upload paths.

## Audio / sound engines (current behavior)
- **Ingest** — `engines/audio/ingest_local` stages directories; `ingest_local_file` stages individual files; `ingest_remote_pull` downloads URIs. Optional GCS upload to `tenant/media/...` when `RAW_BUCKET` is set via `GcsClient`.
- **Preprocess/clean** — `engines/audio/preprocess_basic_clean` applies ffmpeg loudnorm + HPF/LPF into mono 44.1k wav outputs.
- **Segmentation** — `engines/audio/segment_ffmpeg` converts input (audio or video) to mono mp3 then segments into fixed-length chunks with basic start/end seconds metadata.
- **Beat analysis** — `engines/audio/beat_features` uses librosa to compute bpm/downbeats/16th grid; returns zeros if librosa missing.
- **ASR** — `engines/audio/asr_whisper` stub producing empty segments; `engines/audio_core/asr_backend` uses faster-whisper when installed, otherwise emits status `unavailable`. Word timings preserved when available.
- **Slang/punctuation** — `engines/text/normalise_slang` normalizes slang tokens in ASR payloads; `text/clean_asr_punct_case` adds basic casing/punctuation.
- **Alignment** — `engines/align/audio_text_bars` collapses ASR segments into sequential bars (ignores beat metadata). The BBK pipeline has a richer aligner (`pipeline/04_align_words.py`) mapping words to 16-slot bars using beat metadata and syllable counts.
- **Flow tagging** — `engines/tag/flow_auto` and BBK `pipeline/05_auto_tag_flow.py` classify flow style over two-bar chunks (half_time/skippy_140/triplet_machine).
- **Dataset packing** — `engines/dataset/pack_jsonl` (simple) and BBK `pipeline/06_pack_jsonl.py` (rhyme/density metadata) write train/val JSONL for LoRA-style training.
- **Training stubs** — `engines/train/lora_local` and `train/lora_peft_hf` write metadata placeholders; `engines/audio_core/lora_train.py` optionally runs tiny torch loop if installed to emit adapter.pt.
- **Pipelines/entrypoints**
  - Local CLI runners for each atomic audio engine (`runner.py` in each subdir).
  - `engines/audio_core/runner.py` orchestrates clean → beats → ASR → dataset (plus optional LoRA) for local runs; used by BBK service.
  - `engines/bot-better-know/pipeline/ingest.py` orchestrates full grime pipeline with gsutil syncs, faster-whisper ASR, beat alignment, tagging, JSONL packing, and LoRA training; assumes GCS buckets/env vars set.
  - HTTP: `POST /bbk/upload-and-process` accepts a file upload and runs `audio_core` pipeline in a run dir; `POST /bbk/start-training` runs LoRA training on produced dataset.
- **External services/infra**
  - ffmpeg required for ingest/preprocess/segment/frame-grab.
  - faster-whisper optional (ASR stub otherwise) in `audio_core`; BBK pipeline requires it plus `gsutil`, `librosa`, torch for training.
  - GCS used for optional uploads in ingest engines and vector ingest; Firestore via Nexus logging; Vertex embeddings for vector ingest/search (text/image, video treated as text content).
- **Assumptions/limitations**
  - Many engines default tenant to `t_unknown` when not provided; ASR stub returns empty segments.
  - `segment_ffmpeg` discards video (-vn) and reports segment times from zero without mapping back to original video timelines.
  - `align/audio_text_bars` ignores beat metadata entirely; BBK aligner expects beat meta files alongside ASR JSON.
  - Cleaning/beat/ASR/training fail open: optional deps missing yield zeros or “unavailable” but pipelines continue.

## Video vs audio separation
- **Video handling** — Only dedicated video engine is `engines/video/frame_grab`, which extracts still frames at fixed intervals or explicit timestamps and returns `{timestamp_ms, frame_path}` plus `video_meta.source`.
- **Audio from video** — `engines/audio/segment_ffmpeg` accepts video inputs but strips video with `-vn` and treats output as audio-only segments; no linkage back to video frames or original timeline beyond derived start/end seconds.
- **Storage/model representation**
  - Media uploads (`engines/media/service/routes.py`) create `asset_id` + GCS URI stored as `NexusDocument` text with tags; no type differentiation between audio/video.
  - Vector ingest (`engines/nexus/vector_explorer/ingest_routes.py`) allows `content_type` of `video` but requires `text_content` for embedding; any uploaded binary is just stored in raw media bucket with `source_ref.gcs_uri`.
  - Frame grab output holds file paths and timestamps only; audio segments and video frames are not linked by shared IDs or timeline metadata.
- **Contracts/patterns today**
  - “Just sound”: audio engines operate on filesystem paths and return cleaned paths/segments/ASR payloads/bars with minimal context.
  - “Just video”: frame grab returns frames + source; no audio awareness.
  - “Combined AV”: only conceptual in docs (`docs/engines/ENGINE_COMBOS.md` mentions pipelines combining frame grab + ASR), but no implemented module that binds frames to audio/text outputs.

## Multi-tenant / identity as-is
- **Explicit fields** — Many models use `tenantId` (camel) e.g., `DatasetEvent`, audio ingest inputs, temperature engine; Vector Explorer routes require `tenant_id` (snake). BBK service and audio_core pipeline do not take tenant/env at all.
- **Runtime defaults** — `engines/config/runtime_config.py` pulls `TENANT_ID`/`ENV` env vars. Chat pipeline (`engines/chat/pipeline.py`) and media routes fall back to these when tenant/env not provided; logging uses them for events.
- **Persistence** — Nexus Firestore backend prefixes collections by `tenant_id` and writes `tenant_id`/`env` on snippets/events. GCS uploads prepend `tenant/media/...` or `tenant/datasets/...`.
- **Inconsistencies** — Mixed casing (`tenantId` vs `tenant_id`), optional tenant parameters (media upload defaults to env config, Vector Explorer requires explicit), some engines use hardcoded defaults (`t_unknown`) or ignore identity altogether (frame grab, segment, audio_core runner). BBK HTTP flow omits tenant entirely yet can upload to GCS via ingest engines if configured.

## Obvious gaps / questions
- ASR and LoRA implementations are stubs unless heavyweight deps are installed; production-quality transcription/training not wired into engine versions under `engines/audio`/`train`.
- Audio alignment in `engines/align/audio_text_bars` ignores beat/timing; only BBK pipeline does real beat-aware alignment. Should there be a shared, reusable aligner?
- No data model linking video frames to audio segments or transcripts; media uploads and vector ingest store raw URIs without type metadata beyond tags/content_type.
- Segmenter drops video (`-vn`) and resets timestamps from zero; unclear how to align back to source video timelines for combined AV use.
- Tenant/env handling is uneven (defaults vs required vs absent). Should HTTP surfaces converge on one casing and require tenant/env, especially for GCS/Firestore writes?
- BBK service runs pipelines locally with filesystem state and minimal validation; unclear how results map to tenant/asset records or how they’d be surfaced in other services.
