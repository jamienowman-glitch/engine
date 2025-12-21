# Phase 5: Region-Aware Beauty v1

## Overview
This phase introduces a region-aware beauty engine that enables targeted filters like teeth whitening and skin smoothing. It relies on a region analysis step that identifies specific areas (e.g., "teeth", "face") and generates masks for them.

## Core Concepts

### Region Analysis
The `video_regions` engine analyzes a video asset and produces a `RegionAnalysisSummary`. This summary lists temporal segments where specific regions are detected and links to mask artifacts (binary images) that isolate those regions.

### Region-Aware Filters
New filters `TeethWhitenFilter` and `SkinSmoothFilter` are added to the render engine. These filters consume the `RegionAnalysisSummary` to apply their effects only to the masked areas.

## Architecture

### `engines/video_regions`
- **Models**:
    - `RegionMaskEntry`: Time, Region Type ("teeth", "skin", etc.), Mask Artifact ID.
    - `RegionAnalysisSummary`: List of entries.
- **Service**:
    - `analyze_regions(asset_id)`: Stub implementation for V1. Generates deterministic dummy regions/masks.
- **Artifacts**: New kind `video_region_summary`.

### `engines/video_render` Integration
The render engine's plan builder is updated to:
1.  Check if a clip has region-aware filters.
2.  If so, look up the `video_region_summary` artifact for the asset.
3.  Find relevant mask artifacts for the current time/region.
4.  Construct an FFmpeg filter graph that uses `alphamerge` or `overlay` to apply the filter effect only through the mask.

## API

### `POST /video/regions/analyze`
- Input: `AnalyzeRegionsRequest` (asset_id, tenant_id, etc.).
- Output: `AnalyzeRegionsResult` (artifact_id of the summary).

## Future Work
- Replace stub analysis with real ML models (Face parsing, etc.).
- improved tracking and temporal consistency.
