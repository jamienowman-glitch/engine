# NorthStar Engines · Overview

This repo is for reusable engines that power the wider NorthStar system.

## 1. Engine Families

We group engines into four main families:

1. Audio
   - ASR (speech-to-text)
   - TTS (text-to-speech)
   - Music / SFX generation
   - Mixing, normalisation, basic mastering

2. Video
   - Cutting / clipping
   - Captioning / subtitling
   - Overlays / simple templates
   - Basic compositing pipelines

3. 3D
   - Layout engines for 3D scenes
   - Helpers to map from abstract layouts (e.g. 24-unit mental grids) to world space
   - Scene graph utilities

4. Analytics
   - Metrics calculation
   - Dashboards / score aggregation logic
   - Simple anomaly detection and thresholds

## 2. Design Principles

- Engines are:
  - Configurable via clear data structures.
  - Composable.
  - Testable and predictable.

- Engines avoid:
  - Hiding magic config in code.
  - Embedding secrets.
  - Unbounded side effects.

## 3. Contracts

Each engine should define:

- Input schema
- Output schema
- Config options
- Error modes

These specs live next to the engine implementation files and are referenced by plan tasks.

## 4. Planning

The global backlog and active tasks for engines live in:

- `docs/20_ENGINES_PLAN.md`

