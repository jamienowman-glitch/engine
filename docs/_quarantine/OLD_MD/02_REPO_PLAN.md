# ==============================================================================
# REPO MASTER PLAN
#
# This is the single canonical plans file for this repo.
# All older scattered plan docs are now considered read-only history.
# Future plans must be appended here only.
# ==============================================================================

# HOW TO USE THIS FILE
#
# Every new plan entry gets:
# - a unique sequential ID (e.g., PLAN-023, PLAN-024), continuing from the highest ID.
# - a status field: PENDING, ACTIVE, or DONE.
# - space for each agent to write their notes / results.
#
# Planning agents (e.g., Gem):
# - Create new entries as PENDING.
# - Leave a clear "Implementation Notes for Max" subsection.
# - Specify which engines/areas the plan touches.
#
# Implementer agents (e.g., Max):
# - Change status from PENDING -> ACTIVE when starting work.
# - Change status from ACTIVE -> DONE when finished.
# - Add any technical notes/decisions to the log file.
#
# Reviewer/safety agents (e.g., Claude):
# - Add review notes under a separate "Review Notes" subheading.
# - Do not create new plan IDs, only annotate existing ones.

---
NOTE (System): This is the ONLY planning document for this repo. All agents and humans MUST add/modify tasks here. No other plan files are allowed.

# REPO MASTER PLAN

Status: DONE
Owner: Control Tower (Jay)
Last updated: 2025-11-30

---

## A. Global Overview

This repository contains **engines** for the NorthStar OS. Engines are headless, reusable components that take structured input and produce structured output. They are designed to be driven by other systems, such as UIs, batch jobs, or other agents.

All work in this repo is governed by two key documents:
-   **`docs/00_CONSTITUTION.md`**: The "why" and "how we behave." Defines roles, principles, and safety rules.
-   **`docs/01_FACTORY_RULES.md`**: The "how we build." Defines processes for planning, logging, testing, and file structures.

All tasks are defined below as `ENGINE-XXX` blocks.

---

## B. Engine Tasks

### ENGINE-001 – Core Scene Engine v1

Legacy ID: SE-01
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement a Scene Engine as an HTTP service that accepts a description of a grid and a list of items (`boxes`) and returns a standard 3D Scene JSON object. It supports layout "recipes" to arrange content, starting with a flat "wall" and a 3D "vector_explorer".

**Files to touch**
- `engines/scene-engine/` (and subdirectories for service, core, recipes, tests)
- `engines/scene-engine/Dockerfile`
- `engines/registry/engine_registry.json`
- `docs/logs/ENGINES_LOG.md`

**Phases**
- Phase A – Contracts & Types (✅ DONE)
- Phase B – HTTP Service Skeleton (✅ DONE)
- Phase C – Grid & Box Normalisation Engine (✅ DONE)
- Phase D – Grid→World Mapping & Recipes (✅ DONE)
- Phase E – Engines Registry Hooks (✅ DONE)
- Phase F – Docker & Local Container (✅ DONE)
- Phase G – Minimal Deployment Lane (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you start this engine, set `Status: ACTIVE`.
  - When you finish all phases, set `Status: DONE` and add a one-line completion note with date.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note under this block.

Completed: 2025-11-30 – Registry entries and combos added for Scene Engine components.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-002 – Atomic Engine: audio/ingest_local

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `audio/ingest_local` atomic engine, which syncs a local directory or GCS inbox to the local working directories.

**Files to touch**
- `engines/audio/ingest_local/types.py`
- `engines/audio/ingest_local/engine.py`
- `engines/audio/ingest_local/tests/test_ingest_local.py`
- `engines/audio/ingest_local/runner.py`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you start this engine, set `Status: ACTIVE`.
  - When you finish all phases, set `Status: DONE` and add a one-line completion note with date.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note under this block.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-003 – Atomic Engine: audio/ingest_local_file

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `audio/ingest_local_file` atomic engine, which stages local audio/video files into a working inbox.

**Files to touch**
- `engines/audio/ingest_local_file/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-004 – Atomic Engine: audio/ingest_remote_pull

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `audio/ingest_remote_pull` atomic engine, which pulls remote audio/video to local staging.

**Files to touch**
- `engines/audio/ingest_remote_pull/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-005 – Atomic Engine: audio/preprocess_basic_clean

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `audio/preprocess_basic_clean` atomic engine for basic noise/level cleanup.

**Files to touch**
- `engines/audio/preprocess_basic_clean/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-006 – Atomic Engine: audio/segment_ffmpeg

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `audio/segment_ffmpeg` atomic engine to segment audio using FFmpeg.

**Files to touch**
- `engines/audio/segment_ffmpeg/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-007 – Atomic Engine: audio/asr_whisper

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `audio/asr_whisper` atomic engine as a wrapper for Whisper ASR.

**Files to touch**
- `engines/audio/asr_whisper/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-008 – Atomic Engine: text/normalise_slang

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `text/normalise_slang` atomic engine for slang-preserving text normalization.

**Files to touch**
- `engines/text/normalise_slang/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-009 – Atomic Engine: text/clean_asr_punct_case

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `text/clean_asr_punct_case` atomic engine to restore punctuation and casing.

**Files to touch**
- `engines/text/clean_asr_punct_case/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-010 – Atomic Engine: audio/beat_features

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `audio/beat_features` atomic engine to analyze beat and tempo.

**Files to touch**
- `engines/audio/beat_features/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-011 – Atomic Engine: align/audio_text_bars

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `align/audio_text_bars` atomic engine to align words to musical bars.

**Files to touch**
- `engines/align/audio_text_bars/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-012 – Atomic Engine: tag/flow_auto

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `tag/flow_auto` atomic engine for rule-based flow tagging.

**Files to touch**
- `engines/tag/flow_auto/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-013 – Atomic Engine: dataset/pack_jsonl

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `dataset/pack_jsonl` atomic engine to package data into JSONL format.

**Files to touch**
- `engines/dataset/pack_jsonl/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-014 – Atomic Engine: train/lora_local

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `train/lora_local` atomic engine as a placeholder for local LoRA training.

**Files to touch**
- `engines/train/lora_local/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-015 – Atomic Engine: train/lora_peft_hf

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `train/lora_peft_hf` atomic engine for LoRA fine-tuning via PEFT/HuggingFace.

**Files to touch**
- `engines/train/lora_peft_hf/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-016 – Atomic Engine: video/frame_grab

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `video/frame_grab` atomic engine to grab representative frames from video uploads.

**Files to touch**
- `engines/video/frame_grab/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-017 – Chat Surface & Core Contracts

Legacy ID: C-01
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Define the HTTP contracts and data shapes used by the shared Chat Surface across all apps. This creates the thin Python service layer that receives chat requests, calls internal engines, and streams back responses, without any specific backend (e.g., ADK) wiring.

**Files to touch**
- `engines/chat/service/`
- `engines/chat/tests/`

**Phases**
- Phase A – Chat Contracts & Schemas (✅ DONE)
- Phase B – Chat Service Skeleton (✅ DONE)
- Phase C – Message Actions Contracts (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – All phases for defining chat contracts and service stubs are complete.
QA: PASS (2025-11-30) - Schemas, routes, and stubs are implemented as per the plan.

---

### ENGINE-018 – Guardrails: Strategy Lock & 3-Wise LLM

Legacy ID: G-01
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Define the core guardrail engines that sit behind the chat actions: the Strategy Lock planner and the 3-Wise LLM risk panel. These are pure, internal engines with no external API calls.

**Files to touch**
- `engines/guardrails/strategy_lock/`
- `engines/guardrails/three_wise/`

**Phases**
- Phase A – Strategy Lock Engine Plan (✅ DONE)
- Phase B – 3-Wise LLM Engine Plan (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Contracts and stub engines for Strategy Lock and 3-Wise LLM are complete.
QA: PASS (2025-11-30) - Schemas and stub `run()` functions are implemented as planned.

---

### ENGINE-019 – PII & Data Hygiene

Legacy ID: P-01
Status: DONE
Planner Gil
Implementer: Max
QA: Claude

**Goal**
Define reusable engines for stripping PII from text and creating `DataPolicyDecision` attachments to flag data safety for training purposes.

**Files to touch**
- `engines/guardrails/pii_text/`

**Phases**
- Phase A – Text PII Strip Engine (✅ DONE)
- Phase B – PII Policy Attachments (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – PII stripping engine contracts and policy schemas are complete.
QA: PASS (2025-11-30) - All specified schemas and stub engines are implemented.

---

### ENGINE-020 – Temperature, KPIs & Budgets

Legacy ID: T-01
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Provide a single control brain for Temperature bands, KPI corridors, and budget ceilings/floors by defining the core state schemas and a stub Temperature engine.

**Files to touch**
- `engines/control/state/`
- `engines/control/temperature/`

**Phases**
- Phase A – State Schemas & Mechanical Names (✅ DONE)
- Phase B – Temperature Engine Plan (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Control plane state schemas and Temperature engine contracts are complete.
QA: PASS (2025-11-30) - All specified schemas and stub engines are implemented.

---

### ENGINE-021 – Nexus & Datasets

Legacy ID: N-01
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Define how engines interact with Nexus (data/research/style) and how training examples are logged in a PII-safe way by defining the core schemas for spaces and events.

**Files to touch**
- `engines/nexus/`
- `engines/dataset/events/`

**Phases**
- Phase A – Nexus Spaces & IDs (✅ DONE)
- Phase B – Dataset Event Schema (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Nexus and Dataset event schemas are defined and implemented.
QA: PASS (2025-11-30) - All specified schemas are implemented and tested.

---

### ENGINE-022 – SEOUTM & Event Logging

Legacy ID: S-01
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Ensure all logging is built with SEO/UTM-awareness from Day One by defining a central logging engine that consumes the canonical `DatasetEvent`.

**Files to touch**
- `engines/logging/events/`

**Phases**
- Phase A – Logging Engine Plan (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – The central logging engine contract is defined and stubbed.
QA: PASS (2025-11-30) - Stub engine and tests are implemented as planned.

---

## C. Completed Engines

| Engine ID | Name | Status | QA |
|---|---|---|---|
| ENGINE-001 | Core Scene Engine v1 | DONE | PASS |
| ENGINE-002 | Atomic Engine: audio/ingest_local | DONE | PASS |
| ENGINE-003 | Atomic Engine: audio/ingest_local_file | DONE | PASS |
| ENGINE-004 | Atomic Engine: audio/ingest_remote_pull | DONE | PASS |
| ENGINE-005 | Atomic Engine: audio/preprocess_basic_clean | DONE | PASS |
| ENGINE-006 | Atomic Engine: audio/segment_ffmpeg | DONE | PASS |
| ENGINE-007 | Atomic Engine: audio/asr_whisper | DONE | PASS |
| ENGINE-008 | Atomic Engine: text/normalise_slang | DONE | PASS |
| ENGINE-009 | Atomic Engine: text/clean_asr_punct_case | DONE | PASS |
| ENGINE-010 | Atomic Engine: audio/beat_features | DONE | PASS |
| ENGINE-011 | Atomic Engine: align/audio_text_bars | DONE | PASS |
| ENGINE-012 | Atomic Engine: tag/flow_auto | DONE | PASS |
| ENGINE-013 | Atomic Engine: dataset/pack_jsonl | DONE | PASS |
| ENGINE-014 | Atomic Engine: train/lora_local | DONE | PASS |
| ENGINE-015 | Atomic Engine: train/lora_peft_hf | DONE | PASS |
| ENGINE-016 | Atomic Engine: video/frame_grab | DONE | PASS |
| ENGINE-017 | Chat Surface & Core Contracts | DONE | PASS |
| ENGINE-018 | Guardrails: Strategy Lock & 3-Wise LLM | DONE | PASS |
| ENGINE-019 | PII & Data Hygiene | DONE | PASS |
| ENGINE-020 | Temperature, KPIs & Budgets | DONE | PASS |
| ENGINE-021 | Nexus & Datasets | DONE | PASS |
| ENGINE-022 | SEOUTM & Event Logging | DONE | PASS |

---

## D. Parking Lot / Future Engines

- **Scene Engine Animations:** Add support for describing smooth transitions for camera and nodes when the scene layout changes.
- **Scene Engine Live Updates:** Implement SSE or WebSocket support to push partial updates to clients for dynamic scenes.
- **Scene Engine Advanced Projection:** Enhance the `"vector_explorer"` recipe with more advanced dimensionality reduction techniques (e.g., UMAP, t-SNE).
- **BBK Studio Recipes:** Develop recipes specific to the BBK Studio, such as arranging stems, loops, and effects in a 3-D DAW-like interface.
- **Shop Layout Recipes:** Develop recipes for e-commerce, such as dynamic product walls, KPI dashboards, and interactive funnels.

---
# NEW PLANS
---

### PLAN-023: SQUARED OS v0 – CORE INFRA & ENGINES (NO APP LOGIC)

Status: DONE
Owner: Gem (Planner)
Last updated: 2025-12-01

**Goal**: To establish the core infrastructure and connect the essential "brain" engines of the SQUARED OS. This phase focuses purely on the foundational plumbing, with no application-specific behavior. The OS should be able to process a request, apply guardrails, interact with data, and log events securely.

---

#### Phase 0 – Lock contracts, not logic

**Goal**: Contracts and shapes are stable enough that infra work isn’t wasted. No app behaviour defined yet. No app logic in engines.

**Tasks**:
- **Task 0.1**: Confirm and document the canonical shapes for: Surface, App, Federation, Cluster, Gang, Agent.
- **Task 0.2**: Re-state the rule: Engines handle structure, routing, storage, and external calls. Agents (LLM calls + manifests) handle behaviour and judgement.
- **Task 0.3**: Mark which engines are required for OS v0. The required engines are:
    - `ENGINE-017` – Chat surface engine
    - `ENGINE-018` – Guardrails engine (Strategy Lock + 3-Wise)
    - `ENGINE-019` – PII/Data hygiene engine
    - `ENGINE-020` – KPI/Budget state + Temperature trigger engine
    - `ENGINE-021` – Nexus & datasets engine
    - `ENGINE-022` – SEO/UTM/Event logging engine
    - Any minimal ingest/log helpers required.
- **Task 0.4**: Mark all other engines as `NOT_REQUIRED_FOR_OS_V0` in a central registry (e.g., `engines/registry/engine_registry.json` with a status flag).
- **Task 0.5**: Ensure any “Temperature engine” or “CEO engine” does not contain behaviour. Temperature classification must be done by a Temperature agent (LLM call) using Nexus data + language definitions. A CEO view must be a combination of a Nexus space for “CEO signals”, a layout template, and a CEO ranking agent (LLM), not an engine.

**Implementation Notes for Max**:
Do not modify any engine to add app-specific behaviour. Engines only know about surfaces, tenants, cards, Nexus, events and external services.

---

#### Phase 1 – Core infra & secrets (GCP + AWS)

**Goal**: One solid backbone so engines have real services to talk to. This is infra + configuration only, still no app behaviour.

**Tasks**:
- **Task 1.1 (GCP)**: Ensure Vertex/LLM endpoints are available for: a generic chat/orchestrator agent, Temperature agent, CEO view agent, and helper agents (PII/UTM/SEO, etc.).
- **Task 1.2 (GCP)**: Define GSM (Google Secret Manager) keys for: Vertex/LLM access, and any other core secrets needed by engines.
- **Task 1.3 (GCP)**: Ensure there is a Cloud Run base service (or equivalent) for engines, with a single network and a single service account with only required permissions.
- **Task 1.4 (AWS)**: Confirm that one AWS account/OU is set up with a primary region.
- **Task 1.5 (AWS)**: Define S3 buckets for: raw uploads, datasets, and exports.
- **Task 1.6 (AWS)**: Define a database for Nexus metadata/state (e.g., RDS Postgres or DynamoDB).
- **Task 1.7 (AWS)**: Define a logging destination (e.g., CloudWatch log group).
- **Task 1.8 (AWS)**: Define IAM roles for: engines, admin, and read-only access.
- **Task 1.9 (Secrets)**: Ensure all coordinates (DB URLs, bucket names, etc.) come from GCP Secrets (GSM) or AWS Secrets (SSM/Secrets Manager).

**Implementation Notes for Max**:
When wiring engines, always read configuration from secrets or environment variables. Never hard-code ARNs, project IDs, or bucket names in engine code.

---

#### Phase 2 – Plumb the “core brain” engines (no media, no app behaviour)

**Goal**: For one test tenant + one surface, the OS can: accept chat, call LLM with manifests, read/write to Nexus, compute Temperature via agent, apply Guardrails via agent, and log events safely.

**Tasks**:
- **Task 2.1 (Chat surface engine)**:
    - Wire to the chosen LLM endpoint.
    - Add basic auth (API key/JWT is enough for v0).
    - Connect to a conversation state store (e.g., Redis, Postgres, Firestore).
    - Make it read from cards to know which surface/app/federation/agent is being invoked and which Nexus spaces are relevant.
    - Ensure it can stream tokens back to the UI (Decision needed: SSE or WebSocket).
- **Task 2.2 (Nexus & datasets engine)**:
    - Back Nexus by the real DB chosen in Phase 1.
    - Implement minimal, generic operations: `write_snippet`, `write_event`, `query_by_tags`, `query_for_agent`.
    - Namespace by tenant + surface and by space (style/data/research/state etc.), not by app.
- **Task 2.3 (KPI/Budget state + Temperature trigger engine)**:
    - Store KPI snapshots and budget bands in Nexus.
    - Provide methods to: update KPI state, retrieve current KPI state, call the Temperature agent (LLM) with KPI state + language definitions.
    - Persist `temperature_band` + explanation back to Nexus.
    - The engine must not contain formulas or thresholds; it only orchestrates storage and LLM calls.
- **Task 2.4 (Guardrails engine)**:
    - **Strategy Lock**: Given a proposed action + surface policies, call LLM to build a plan/summary and identify risks. Store “plan objects” in a `strategy_lock` Nexus space.
    - **3-Wise**: Call multiple LLM prompts/models, aggregate critiques, and store results in Nexus.
- **Task 2.5 (PII & Data hygiene engine)**:
    - Implement PII detection/masking via regex/heuristics for email, phone, address, order IDs, etc.
    - This engine wraps around anything being written into logs, Nexus history, or outbound events.
- **Task 2.6 (SEO/UTM & Event logging engine)**:
    - Provide a `log_event` function that calls the PII engine, enriches with UTM/SEO context, and ships structured events to the logging backend from Phase 1.
    - The engine must be generic, with fields like tenant, surface, engine, severity, payload.

---

#### Phase 3 – Generic app wiring test (still no behavioural definitions)

**Goal**: Prove that the OS slice can support any future app without changing engine code.

**Tasks**:
- **Task 3.1**: Define one simple placeholder App card that only defines which surface it belongs to, which federations/agents it would use, which Nexus spaces it touches, and which events it might emit.
- **Task 3.2**: Define one placeholder Federation that can call the Chat surface, read/write to Nexus, trigger Temperature/Guardrails, and emit a generic event.
- **Task 3.3**: Confirm that with the placeholder app/federation card in place, engines 017-022 can support the flow without any engine code referring to specific app semantics.

---

#### Phase 4 – Harden & extend (after OS v0 is proven)

**Goal**: Harden the OS and prepare for extension.

**Tasks**:
- **Task 4.1 (Harden)**: Implement robust logging, metrics, autoscaling, retries, and back-pressure.
- **Task 4.2 (Extend)**: Connect media engines (ASR, video, etc.), add new Nexus spaces as needed, and prepare for app-level card definitions.
- **Task 4.3 (Rule)**: Explicitly state that no app behaviour may be implemented in engines without a corresponding app/federation card defined first. Behaviour always lives in language cards + agents, never hard-coded.

---

**Execution rules**:
- **Planners (Gem)**: Mark new entries and tasks as `PENDING`.
- **Implementers (Max)**:
    - Set status to `ACTIVE` when starting work.
    - Log problems and solutions in the single log file with `PLAN_ID`.
    - Set status to `DONE` when finished, adding notes and artefact locations to the log.

Completed: 2025-12-01 – Repo-side deliverables created (contracts doc, infra/secret specs, registry OS v0 status map, placeholder app/federation cards, hardening notes). Engine code unchanged; external infra remains to be provisioned.

    - `KLAVIYO.ADD.TO_LIST_V1`
---

### PLAN-024: Universal Chat & Transports v0 (Repo-only)
- **Task 6.2**: Register these new IO contracts in the engine/connector registry so they can be referenced by ADK cards. Note: This task is for defining the schemas only; implementation will occur in the connectors repository.

---
Status: DONE
#### Phase 7 – Final Review: No App Logic in Engines
Owner: Max
**Goal**: Guarantee the separation of concerns between engines and application logic.**Tasks**:
Planner: Gil
- **Task 7.2**: Confirm that all such behavioral logic resides exclusively in the cards and orchestration layer managed by the ADK.
Last updated: 2025-12-01


/≥### PLAN-026: CHAT_NEXUS_VERTEX_PROD_WIRING_DEV**!!!--- PRODUCTION WIRING ---!!!**
**Goal**: To prepare the repository for a universal chat system with multiple transport layers (HTTP, WebSocket, SSE). This is a "repo-only" task, meaning no external infrastructure, LLMs, or databases should be provisioned or connected. It is about setting up the contracts and stubs for a front-end to build against locally.


**!!!--- PRODUCTION WIRING ---!!!**Status: DONE
---
Agent: Max


#### Phase 0 - Contracts & Stubs

**Goal**: Define stable contracts and implement stubbed, in-memory transport layers.

**Tasks**:
- **Task 0.1: Define Data Contracts**:
    - Implement Pydantic (or similar) schemas for `Thread`, `Message`, and `Contact`.
    - These contracts should be neutral and application-agnostic.
    - Location: `engines/chat/contracts.py` (or a suitable new location).

- **Task 0.2: Implemment Stubbed HTTP Transport**:
    - Create a FastAPI service with stubbed endpoints:
        - `GET /chat/threads`
        - `POST /chat/threads`
        - `GET /chat/threads/{id}/messages`
        - `POST /chat/threads/{id}/messages`
    - Use an in-memory dictionary for data storage.
    - The `POST /.../messages` endpoint should trigger a hardcoded agent echo reply.
    - Location: `engines/chat/service/http_transport.py`

- **Task 0.3: Implement Stubbed WebSocket Transport**:
    - Create a WebSocket endpoint: `/ws/chat/{thread_id}`.
    - It should handle `join` and `message` events from the client.
    - It should broadcast messages to all subscribers on a thread using an in-memory manager.
    - Location: `engines/chat/service/ws_transport.py`

- **Task 0.4: Implement Stubbed SSE Transport**:
    - Create an SSE endpoint: `/sse/chat/{thread_id}`.
    - It should send a `message` event whenever a new message is added to the thread from any transport.
    - Location: `engines/chat/service/sse_transport.py`

- **Task 0.5: Implement Transport Abstraction**:
    - Create a simple pub/sub abstraction that the HTTP, WebSocket, and SSE transports can use to communicate.
    - e.g., `publish_message(thread_id, message)` and `subscribe_to_thread(thread_id, callback)`.
    - This allows a message posted to the HTTP endpoint to be broadcast to WebSocket and SSE clients.
    - Location: `engines/chat/service/transport_layer.py`

- **Task 0.6: Add Tests & Documentation**:
    - Add basic unit/integration tests for the contracts and each transport layer.
    - Create a `README.md` inside the `engines/chat` directory explaining that this is a stub implementation for local development.

**Implementation Notes for Max**:
- All work is repo-only. Do not add any cloud dependencies or external service calls.
- All data is transient and stored in-memory.
- Clearly mark stubbed logic (e.g., agent replies) with code comments.
- Follow the existing conventions for file structure and testing.

---
### PLAN-025: CAIDENCE² Engine Readiness

**!!!--- PRODUCTION IMPLEMENTATION ---!!!**
**NOTE: THIS IS A PRODUCTION PLAN. ALL WORK MUST BE PRODUCTION-READY. NO STUBS ARE PERMITTED. ALL CONNECTIONS TO SERVICES (LLMS, DATABASES, APIS) MUST BE REAL AND USE THE PRODUCTION CONFIGURATIONS AND SECRETS. THIS IS A GO-LIVE PLAN.**
**!!!--- PRODUCTION IMPLEMENTATION ---!!!**

Status: PENDING
Owner: Max
Planner: Gil
Last updated: 2025-12-01
AREA: engines

**Goal**: Make existing engines usable for the CAIDENCE² application by ensuring they are properly integrated and configured, without adding any application-specific logic into the engines themselves. All behavior must be driven by cards from the ADK.

---

#### Phase 1 – Engine Inventory for CAIDENCE² Needs

**Goal**: Map existing engines to CAIDENCE² functional roles and identify any gaps.

**Tasks**:
- **Task 1.1**: Create a mapping document (`docs/caidence2/engine_mapping.md`) that inventories existing engines against these required roles:
    - Chat surface / orchestrator
    - Nexus read/write
    - PII strip / Data hygiene
    - Guardrails (Strategy Lock + 3-Wise LLM)
    - Temperature / KPI band engine
    - SEOUTM & logging
- **Task 1.2**: In the mapping document, mark each engine's status:
    - **Ready**: Can be used as-is.
    - **Needs IO Tweak**: Requires minor adjustments to its input/output contracts.
    - **Needs Adapter**: Requires a thin adapter layer to be compatible.

---

#### Phase 2 – Chat Engine / Streaming Readiness

**Goal**: Ensure the main chat engine can serve CAIDENCE² requests and stream responses.

**Tasks**:
- **Task 2.1**: Verify the chat surface engine correctly handles requests specifying `app_id: 'caidence2'` and a valid `tenant_id`.
- **Task 2.2**: Confirm that the engine can stream responses via Server-Sent Events (SSE) and is designed in a way that a WebSocket bridge could be added later without a major refactor.
- **Task 2.3**: Ensure that all prompts and operational parameters are derived from a card-based manifest passed from the ADK, with no hard-coded prompts in the engine.

---

#### Phase 3 – Nexus Engine for CAIDENCE²

**Goal**: Ensure the Nexus engine can manage CAIDENCE² data spaces.

**Tasks**:
- **Task 3.1**: Verify the Nexus engine can correctly read from and write to the CAIDENCE² spaces as defined by the ADK. These spaces include:
    - `style_nexus`
    - `content_nexus`
    - `schedule_nexus`
    - `performance_nexus`
- **Task 3.2**: Confirm that all Nexus operations respect `tenant_id` and `app_id` for data isolation. Schemas for these spaces will be provided via cards.

---

#### Phase 4 – PII & Logging Integration

**Goal**: Ensure all data flowing through the system is properly logged and sanitized.

**Tasks**:
- **Task 4.1**: Verify the PII engine can reliably strip or mask sensitive information (emails, names, addresses) from the following data types: chat logs, schedule entries, and connector logs.
- **Task 4.2**: Confirm the central logging engine correctly accepts `DatasetEvent` entries for all relevant CAIDENCE² events, including app-specific events, calls to external connectors (YouTube, Slack, etc.), and guardrail decisions.
- **Task 4.3**: Ensure all data is passed through the PII filter before being persisted to any log or database.

---

#### Phase 5 – Guardrails & Temperature Integration

**Goal**: Integrate the decision-making and risk-assessment engines.

**Tasks**:
- **Task 5.1**: Ensure the Strategy Lock and 3-Wise LLM guardrail engines are callable by CAIDENCE² federations via the ADK, with no direct coupling.
- **Task 5.2**: The Temperature engine must be configured to:
    - Read KPI snapshots from the `performance_nexus`.
    - Call the designated LLM agent to assign a temperature band (`cold`, `sweet_spot`, `hot`).
    - Write the resulting temperature band and rationale back into the `performance_nexus`.

---

#### Phase 6 – Connector IO Contracts

**Goal**: Define the data contracts for external service connectors that CAIDENCE² will use.

**Tasks**:
- **Task 6.1**: Define and create the Pydantic schema files for the following connector IO contracts (request/response shapes):
    - `YOUTUBE.POST.CONTENT_V1`
    - `SLACK.SEND.MESSAGE_V1`
    - `ICAL.FEED.UPDATE_V1`




- **Task 7.1**: Conduct a final review of all modified engine code to ensure no CAIDENCE²-specific logic (e.g., "what to post," "when to post") has been hard-coded.
---

**NOTE: THIS IS A PRODUCTION-MODE PLAN FOR THE 'northstar-os-dev' ENVIRONMENT. NO STUBS. NO ECHO AGENTS. ALL SERVICES AND BACKENDS (GCP, FIRESTORE, ADK/VERTEX) MUST BE REAL.**

Summary: Wire chat transports to real LLM (Vertex), Nexus (Firestore), and GCS buckets using GSM secrets for Tenant 0. No stubs.
Scope: CAIDENCE² dev vertical slice – Chat + Nexus + Media, wired to ADK (no external connectors)
Reference Tenant: `t_northstar-dev` (from GSM `northstar-dev-tenant-0-id`)














---
---
---
---
---
---
---
---
---
---
---
---
---
---
---

**✅ Goal**
- For tenant `t_northstar-dev`, we want:
- Real chat via ADK/Vertex (no echo stubs).
- A real blackboard per conversation stored in Nexus/Firestore.
- Real media ingest:
    - Upload from the UI → GCS raw bucket via engines.
    - Metadata persisted into Nexus/Firestore so the UI “stack” can list and display items.
- All of this running as a Cloud Run service using the existing `northstar-dev-engines` service account and GSM secrets.
- No external connectors yet (no YouTube/Slack/Klaviyo).

---

**📂 1. Environment + Config**

- **1.1**: Define or update an engine config file (e.g., `engines/config/env_dev.py`) that:
    - Reads:
        - `TENANT_ID` from GSM secret `northstar-dev-tenant-0-id`
        - `RAW_BUCKET` from GSM secret `northstar-dev-raw-bucket`
        - `DATASETS_BUCKET` from GSM secret `northstar-dev-datasets-bucket`
        - `NEXUS_BACKEND` from GSM secret `northstar-dev-nexus-backend`
    - Uses Application Default Credentials (ADC) for auth, no API keys.
    - Exposes a simple `get_settings()` function that other engines can import.
- **1.2**: Add a small doc: `docs/infra/ENGINES_DEV_RUNTIME.md` that explains:
    - How engines discover the runtime environment:
        - Project ID: `northstar-os-dev`
        - Region: `us-central1`
        - Service Account: `northstar-dev-engines@northstar-os-dev.iam.gserviceaccount.com`
    - That for dev, we assume Cloud Run + Firestore + GCS, all authenticated via ADC.

---

**🧱 2. Nexus Persistence (Firestore)**

- **2.1**: Implement a Nexus backend adapter if one does not already exist (e.g., `engines/nexus/backends/firestore.py`) that:
    - Uses Firestore Native in `us-central1`.
    - Can:
        - `write_snippet(tenant_id, space, payload)` – stores a document.
        - `write_event(tenant_id, event)` – stores `DatasetEvents`.
        - `query_by_tags(tenant_id, space, tags, limit)` – minimal filter.
    - Uses `t_northstar-dev` as the tenant in dev, but never hardcodes it in the functions; it must always be passed in via context.
- **2.2**: Wire the existing Nexus contracts to this backend so that any new chat session, media upload, or auto-generated content preview writes at least one Nexus snippet and one `DatasetEvent`.

---

**💬 3. Universal Chat (PLAN-024 follow-up, no stubs)**

- **3.1**: Take the existing chat contracts + transports from `engines/chat/` and remove/retire the “agent echo” stub behavior.
- **3.2**: Implement a real processing pipeline: `HTTP/WS/SSE → chat service → ADK/Vertex call → Nexus write → streamed response`.
- **3.3**: Implement an ADK/Vertex client layer (e.g., `engines/chat/service/llm_client.py`) that:
    - Uses ADC to call Vertex AI (Gemini is fine).
    - Accepts `tenant_id`, an `agent_manifest` (from cards), `conversation_history` (from Nexus), and `blackboard_state`.
    - Returns a streaming iterator of tokens for the SSE/WebSocket transports to forward to the client.
- **3.4**: Wire the transports for real use:
    - **HTTP**: Simple “send message, get complete reply”.
    - **WebSocket + SSE**: Proper streaming of tokens from the ADK call to the client.

---

**🎞 4. Media Ingest + Stack Listing**

- **4.1**: Implement a media ingest endpoint (e.g., `POST /media/upload`) in the main engines API that:
    - Accepts a multipart upload containing the file, `tenant_id`, and optional tags.
    - Writes the file to the `RAW_BUCKET` (`gs://northstar-os-dev-northstar-raw`) under the path: `<tenant_id>/media/<uuid>/<filename>`.
    - Writes a Nexus record to the `media` space with the payload: `{ tenant_id, asset_id, gcs_path, mime_type, tags, created_at }`.
    - Emits one `DatasetEvent` describing the upload.
- **4.2**: Implement a list endpoint (e.g., `GET /media/stack`) that:
    - Accepts `tenant_id` and optional filters.
    - Reads from the Nexus backend (not GCS) to return a list of recent media items for the UI to render.
- **4.3**: Add tests for upload → GCS write, upload → Nexus write, and that the stack listing returns what was written.

---

**🚀 5. Cloud Run Dev Deployment**

- **5.1**: Add or update a minimal Cloud Run deployment manifest (e.g., `deploy/dev/engines-chat.yaml`) that:
    - Deploys the chat + media service as a single container.
    - Uses the service account `northstar-dev-engines@northstar-os-dev.iam.gserviceaccount.com`.
    - Sets required environment variables for `GCP_PROJECT_ID`, `GCP_REGION`, and any GSM secret names.
- **5.2**: Add a short deployment script (e.g., `deploy/dev/deploy_chat.sh`) that runs `gcloud run deploy ...` with the correct flags and the manifest.

---

**🧾 6. Logging & PII Hygiene**

- **6.1**: Ensure the chat and media endpoints use the PII/Data Hygiene engine before writing any logs or Nexus records.
- **6.2**: Ensure a `DatasetEvent` is shipped into the logging engine for each chat turn and each media upload.
- **6.3**: Update the canonical log file (`docs/logs/ENGINES_LOG.md`) with:
    - What changed.
    - Where the new endpoints live.
    - Any final bash commands required to finish infrastructure setup (if anything was discovered to be missing).

---
Max: mark this PLAN as DONE when all tasks are complete and log your work in the canonical log.

Completed: 2025-12-02 – Added Vertex-backed chat pipeline hook, media upload/list endpoints with Nexus/logging, Cloud Run manifest/script, and dev runtime configuration docs.
---
### PLAN-025: INFRA_DEV_BASELINE

Status: DONE
Owner: Gil
Implementer: Max
Last updated: 2025-12-01

**Goal**: Lock northstar-os-dev dev infra, engines SA, Firestore Nexus, GCS buckets, GSM secrets.

**Details**
- Project: `northstar-os-dev`
- Region: `us-central1`
- Service Account: `northstar-dev-engines@northstar-os-dev.iam.gserviceaccount.com`
- Nexus backend: Firestore (native, us-central1)
- GCS buckets: `gs://northstar-os-dev-northstar-raw`, `gs://northstar-os-dev-northstar-datasets`
- GSM secrets: `northstar-dev-tenant-0-id`, `northstar-dev-raw-bucket`, `northstar-dev-datasets-bucket`, `northstar-dev-nexus-backend`
- Required roles on engines SA: `roles/secretmanager.secretAccessor`, `roles/storage.objectAdmin`, `roles/run.invoker`, `roles/aiplatform.user`

Completed: 2025-12-01 – Baseline documented in INFRA_GCP_DEV.md; anti-drift rules added to Constitution.

### PLAN-027 – Temperature Plans & Weighting Pattern (NEW)

- **Goal**: Formalise temperature weighting via Nexus plans; engines stay deterministic.
- **Work**:
  - Define `TemperatureWeightsPlan` schema (tenant/env/weights/note/version).
  - Temperature engine loads latest plan from Nexus (Firestore) with defaults if none.
  - Add service entrypoint to measure temperature: load plan → run engine → log DatasetEvent (kind `temperature_measurement`).
  - Firestore backend helper to fetch latest plan per tenant/env from `temperature_plans_{TENANT_ID}`.
  - Doc the pattern (LLM/DS clusters write plans; engines read only).
  - Tests for default vs planned weights and Nexus helper.

### PLAN-028 – Font Helper & Registry (NEW)

- **Goal**: Provide font/preset tokens for variable fonts (e.g., Roboto Flex) from a registry.
- **Work**:
  - Define font config/preset schemas (font_id, display_name, css_family_name, tracking bounds, presets).
- Registry helper to load fonts (starting with Roboto Flex JSON), fetch preset, clamp tracking, and emit CSS tokens (`fontFamily`, `fontVariationSettings`, `letterSpacing`).
- Docs describing card usage: apps reference font_id + preset_code + tracking; engines return tokens.
- Tests for unknown font/preset, tracking clamp, stable token generation.

### PLAN-029 – PLAN-TEMP-REFINE (Temperature weighting + review loop)

- Define planning vs runtime: runtime temperature measurement reads latest approved plan only; planning job drafts proposals and writes after review.
- Extend TemperatureWeightsPlan (proposed_by, notes, status/version) and store in Firestore `temperature_plans_{TENANT_ID}`.
- Add review/apply helper that reads TemperatureState/KPI history, runs Strategy Lock, and writes approved plans.
- Keep measurement path LLM-free; LLM/DS clusters act only in the planning job.

### PLAN-030 – PLAN-CHAT-ROUTING (multi-scope chat routing + blackboards)

- Add chat scope schema (surface/app/federation/cluster/gang/agent) carried with messages.
- Pipeline persists scope to Nexus/logging and routes to appropriate orchestration stub (surface/app default; scoped routes annotated).
- Tests assert scoped messages appear with scope metadata in Nexus/logging.
- Document scheduled vs on-demand vs reactive distinctions in chat README.

### PLAN-031 – PLAN-REACTIVE-CONTENT (DatasetEvent-driven reactive plays)

- Introduce reactive watcher that consumes DatasetEvents (e.g., content.published.youtube_video) and emits follow-up content.reactive.* events via logging/Nexus.
- Provide hook point for connectors/ingest to trigger watcher.
- Document reactive triggers vs scheduled vs chat triggers; tests for reactive generation.

### PLAN-032 – PLAN-STRATEGY-LOCK-ACTIONS (action classification)

- Classify actions requiring Strategy Lock (+ optional 3-wise) vs those that do not.
- Apply classification to temperature planning job (planning path guarded; runtime measurement not user-facing).
- Document action list for OS/enterprise layer; keep engine keyword logic pluggable.

### PLAN-0AA – Manifest & Token Graph Contract

- **Status**: PENDING
- **Area**: infra/ui-manifests
- **Goal**: Define the canonical JSON/typed shape for manifests, content slots, and tokens (typography/layout/colour/behaviour) across apps/surfaces.
- **Scope**:
  - Path/ID conventions for components, content slots, and token domains.
  - How atoms/views/sections map into the manifest graph; defaults vs current values.
  - Separation of content vs tokens; patch addressing rules.
- **Non-Goals**:
  - No storage/DB or API implementation.
  - No UI or agent wiring; contracts only.
- **Artefacts**:
  - docs/constitution/MANIFEST_TOKEN_GRAPH.md

### PLAN-0AB – Cluster Capabilities & Scoped Patching

- **Status**: PENDING
- **Area**: infra/agents/scopes
- **Goal**: Define capability descriptors for clusters/agents that constrain readable/writable paths and allowed ops; patch contract checked against capabilities.
- **Scope**:
  - Capability schema (allowed_reads/allowed_writes/allowed_ops, cluster metadata).
  - Patch contract (path/op/value, actor metadata) and validation rules.
  - Origin metadata (human/agent, cluster_id/agent_id) expectations.
- **Non-Goals**:
  - No ACL/auth implementation; no runtime validators yet.
  - No transport wiring.
- **Artefacts**:
  - docs/constitution/CLUSTER_CAPABILITIES.md

### PLAN-0AC – Design Tools Scoping (Typography/Layout/Colour/Copy)

- **Status**: PENDING
- **Area**: surfaces/design-tools
- **Goal**: Specialise manifest + capabilities model for creative tools (slides/canvas/video strips) with scoped clusters (typography/layout/colour/copy).
- **Scope**:
  - Representing layers/slides/clips within the manifest graph.
  - Cluster examples for tool families and their allowed paths.
  - Interaction model hints for patching (tokens vs content slots) in creative tools.
- **Non-Goals**:
  - No UI or engine code; no connector/model choices.
- **Artefacts**:
  - docs/constitution/DESIGN_TOOLS_SCOPING.md

### PLAN-0AD – Tiles registry & payload schema

- **Status**: PENDING
- **Area**: surfaces/tiles
- **Summary**: Define extensible tile types and payload fields (id/type/size_hint/strategy_lock_state/actions/timestamps/Nexus refs/pinned) aligned to the manifest/token graph.
- **Detail**:
  - Add tile schema doc; specify registry location and type codes; enforce tight masonry (size_hint is a visual weight, not layout gaps).
  - Tiles carry content refs (Nexus snippets/events, external feed refs) and do not mutate tokens; align with manifest/token graph for UI consumption.
  - Capture minimum mix guidance (KPI + deep content + strategy/next-step) and extensibility for future tile types/sizes.
- **Artefacts**:
  - docs/constitution/TILES_SURFACE.md

### PLAN-0AE – CEO LLM tile-orchestration contract

- **Status**: PENDING
- **Area**: infra/agents/tiles
- **Summary**: Specify how the CEO agent reads Nexus/feeds and emits a ranked tile list—no tile engine math.
- **Detail**:
  - Define request/response contract (inputs: tenant/env/context/filters; outputs: ordered tiles with rationale/trace, Strategy Lock state carried through).
  - Data sources: Nexus snippets/events, external feeds, Strategy Lock status; CEO cluster composes payloads only, respecting cluster capabilities (no direct token writes).
  - Open questions: cadence/trigger model (pull vs push), maximum tile count, rationale retention.
- **Artefacts**:
  - docs/constitution/TILES_SURFACE.md
  - docs/infra/TILES_WIRING.md

### PLAN-0AF – Tiles API surface for UI

- **Status**: PENDING
- **Area**: infra/apis
- **Summary**: Define HTTP/WS contract for requesting tiles (tenant/env/auth) returning PLAN-0AD payloads.
- **Detail**:
  - Specify endpoints/params (e.g., GET /tiles?tenant=...&env=...&surface=...&limit=...; WS/SSE shape if used) and auth expectations.
  - Responses must expose tile payloads (size_hint, strategy_lock_state, actions) without surface grouping in the first view.
  - Open questions: pagination vs cursor, cache headers/ETags, anonymous access (likely none).
- **Artefacts**:
  - docs/infra/TILES_WIRING.md

### PLAN-0AG – Strategy Lock integration in tiles

- **Status**: PENDING
- **Area**: guardrails/strategy-lock
- **Summary**: Define how tiles carry Strategy Lock/3-Wise state and auto-action eligibility.
- **Detail**:
  - Enumerate tile fields for lock status (pending/allowed/blocked), icon hints, and auto-action suggestions (only when pre-cleared).
  - Map to existing Strategy Lock action classifications; no new policy engine; clarify partial approvals/TTL expectations.
  - Open questions: state caching, per-tile action scoping, how to represent “pending review” in UI tokens.
- **Artefacts**:
  - docs/constitution/TILES_SURFACE.md
  - docs/constitution/STRATEGY_LOCK_ACTIONS.md (xref)

### PLAN-0AH – Logging & Nexus events for tiles

- **Status**: PENDING
- **Area**: logging/nexus
- **Summary**: Define DatasetEvent shapes for tile composition, impressions, clicks, and actions.
- **Detail**:
  - Event types (e.g., tiles.composed, tile.impression, tile.action) with required fields: tile_id, type, size_hint, strategy_lock_state, action_ref, timestamps, pinned, order index.
  - Storage expectations in Nexus/Firestore; CEO traces recorded without PII; align with manifest/token graph and cluster capabilities (logging only, no token mutation).
  - Open questions: sampling vs full fidelity, retention, linkage to blackboards and external feeds.
- **Artefacts**:
  - docs/infra/TILES_WIRING.md

---

### LOG – 2025-12-02 – CAIDENCE Wiring Extensions (Max)

- Added PLAN-027/PLAN-028 entries (temperature plans, font registry).
- Implemented TemperatureWeightsPlan schema, Nexus plan fetch, service entrypoint, and measurement logging; documented in TEMPERATURE_PLANS.md and wiring doc.
- Added Firestore plan helper `get_latest_plan`.
- Added font registry/types with Roboto Flex data, CSS token generation, and tests; documented in FONTS_HELPER.md.

### LOG – 2025-12-02 – Temp refine, chat routing, reactive content, Strategy Lock (Max)

- Added PLAN-029..032 entries for temperature refinement, chat scope routing, reactive content, and Strategy Lock action classification.
- Extended TemperatureWeightsPlan (proposed_by/status), added plan review/apply helper with Strategy Lock guard, and documented runtime vs planning separation.
- Added chat scopes to pipeline/logging plus scope tests; documented scheduled/on-demand/reactive modes in chat README.
- Added reactive content watcher scaffold and docs; Strategy Lock actions documented.

UNPLANNED: CAIDENCE PROD WIRING
- Chat transports now call a pipeline that logs to Nexus/Logging; Firestore backend and GCS adapters added (env-driven, no hard-coded IDs).
- Guardrails/PII/Temperature and SEO/FUME primitives upgraded from stubs; wiring documented in docs/infra/ENGINES_WIRING_CAIDENCE.md.

### LOG – 2025-12-02 – Token Graph & Cluster Scoping plans (Max)

- Added PLAN-0AA/0AB/0AC for manifest/token graph, scoped capabilities, and design-tool scoping; planning-only pass.
- Authored design contracts in docs/constitution/{MANIFEST_TOKEN_GRAPH.md,CLUSTER_CAPABILITIES.md,DESIGN_TOOLS_SCOPING.md}; no engine/runtime changes.

    check
ReadFile...s/ENGINES_LOG.md
stat_minus_1
Thinking
Okay, I'll create and write the updated plan and log files. I have all the information, so I'll construct the full content for docs/02_REPO_PLAN.md, then docs/logs/ENGINES_LOG.md, and then use write_file twice to save them.call:write_file{content:

check
WriteFile02_REPO_PLAN.md -0, +148



