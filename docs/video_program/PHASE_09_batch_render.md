# Phase 9: Batch Render & Preset Orchestration

## Overview
This phase introduces the `video_batch_render` engine, designed to orchestrate the rendering of a single video project into multiple output formats (profiles) simultaneously or sequentially. This allows users to generate "Social Bundle" outputs (Landscape 4K, Vertical 1080p, Square 720p) from a single timeline.

## Core Concepts

### Render Profile
A configuration object defining the output constraints for a specific render job.
- **Resolution**: Width/Height (e.g., 1920x1080, 1080x1920).
- **Format**: Container/Codec (mp4/h264, mov/prores).
- **Aspect Ratio Handling**: Strategy for fitting timeline into target (crop, letterbox, scale).
- **Bitrate/Quality**: Target bitrate or CRF.

### Batch Request
A request containing:
- **Project/Sequence ID**: The source.
- **Profiles**: List of `RenderProfile` or Named Presets found in `video_presets`.
- **Destination**: Where to store outputs.

## Architecture

### `engines/video_batch_render`
- **Responsibility**: Coordinator. Does NOT perform rendering itself (delegates to `video_render`), but plans the jobs.
- **Service**: `BatchRenderService`
    - `plan_batch(req) -> BatchPlan` (Dry run)
    - `execute_batch(req) -> BatchJobResult` (Orchestrates rendering)
    
### Logic
1. **Profile Resolution**: Convert named presets to concrete render settings.
2. **Timeline Adaptation**: If profile requires aspect ratio change (e.g., Landscape -> Vertical), apply "smart crop" logic or default center crop. (V1: Center Crop or Scaling).
3. **Job Dispatch**: Call `video_render` for each profile.
4. **Result Aggregation**: Collect all artifact IDs and return summary.

## API
- `POST /video/batch/plan`: Returns list of jobs that would be run.
- `POST /video/batch/execute`: Runs them.

## Verification
- **Test**: Submit batch with 3 profiles. Verify 3 render jobs are triggered and 3 artifacts are registered.
- **Cache Isolation**: Ensure Profile A's render doesn't clobber Profile B's cache.
