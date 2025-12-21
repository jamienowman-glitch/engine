# Audio Sample / Beat Spine - Master Plan

## Vision
Transform the `northstar` audio stack from a linear processing pipe into a generative sample library. We want to treat every ingested video or audio file as a source of "Audio Atoms" (hits, loops, phrases) that can be reused to build new beats and soundscapes.

Crucially, we maintain **lineage**: every atom "knows" where it came from (Asset ID + Time Window), enabling us to auto-cut video snippets ("Origin Snippets") that correspond to the sounds being used.

## Core Engines (Phase 1-3) [IMPLEMENTED - REAL V2]

### 1. Audio Atoms (`engines/audio_samples/*`)
Three specialized detector engines with real DSP backends (Librosa/FFmpeg):

1.  **`audio_hits` (One-Shots)**:
    -   Backend: `LibrosaHitsBackend`.
    -   Detects onsets using `librosa.onset.onset_detect`.
    -   Slices audio files + Registers `DerivedArtifact(kind="audio_hit")`.
2.  **`audio_loops` (Grooves)**:
    -   Backend: `LibrosaLoopsBackend`.
    -   Detects beats/tempo (`librosa.beat.beat_track`) and finds contiguous stable regions.
    -   Slices audio files + Registers `DerivedArtifact(kind="audio_loop")`.
3.  **`audio_voice_phrases` (Vocals)**:
    -   Backend: `DefaultPhrasesBackend`.
    -   Merges ASR transcript words into phrases using `max_gap_ms`.
    -   Slices audio files + Registers `DerivedArtifact(kind="audio_phrase")`.

### 2. Sample Library (`engines/audio_sample_library`)
A query layer that indexes the above artifacts per-tenant.
-   **API**: `GET /audio/sample-library/samples`
-   **Function**: Discovery and filtering (by BPM, bars, confidence, type).
-   **No new state**: Rely entirely on `media_v2` artifacts.

### 3. Pipeline (`engines/audio_field_to_samples`)
An orchestration engine that runs the detectors on raw assets.
-   **Input**: Field recording / Video audio.
-   **Process**: Preprocess (clean) -> Run Detectors -> Register Artifacts.
-   **Result**: Populated sample library.

## Future: Origin Snippets (Phase 4 Scaffold)
*Goal: When a beat is made using these samples, generate a video montage of their sources.*

**Hook**:
-   Input: List of `(audio_artifact_id, start_offset_ms)` used in a beat.
-   Process:
    -   Resolve artifact -> `parent_asset_id` (Video) + `source_start_ms` / `source_end_ms`.
    -   Construct a `video_timeline` Sequence placing those video clips in sync with the beat events.
-   Output: A "Visualizer" video timeline.

## Data Model (Lineage)
We leverage `engines/media_v2.DerivedArtifact`:
-   `parent_asset_id`: The source video/audio.
-   `start_ms` / `end_ms`: The window in the source.
-   `kind`: `audio_hit`, `audio_loop`, `audio_phrase`.
-   `meta`: Contains engine-specific data (`bpm`, `peak_db`, `transcript`).

## Constraints
-   **Engines Only**: No UI/Product logic in this layer.
-   **Deterministic**: Same input -> Same artifacts.
-   **Additive**: Does not break existing audio timelines.
