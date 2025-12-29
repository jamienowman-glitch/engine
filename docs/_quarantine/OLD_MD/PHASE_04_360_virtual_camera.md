# Phase 4: 360 / Virtual Camera v1

## Overview
This phase enables Northstar to handle 360-degree (equirectangular) video assets and "bake" them into standard perspective videos using a virtual camera path.

## Core Concepts

### 360 Assets
Standard `MediaAsset`s with additional metadata:
- `is_360`: boolean (default `False`).
- `projection`: string (default `None`, typically `"equirectangular"`).

### Virtual Camera
A **Virtual Camera Path** defines how the view changes over time within the spherical video. It consists of keyframes controlling:
- **Yaw**: Horizontal rotation (0-360).
- **Pitch**: Vertical rotation (-90 to 90).
- **Roll**: Tilt (-180 to 180).
- **FOV**: Field of View (zoom).

## Architecture

### `engines/video_360`
Atomic engine responsible for:
1.  **Path Management**: CRUD for `VirtualCameraPath`.
2.  **Rendering**: Compiling paths into FFmpeg `v360` filter commands to reframe the video.

### Rendering Logic (V1)
The engine uses the FFmpeg `v360` filter.
- Input: Equirectangular 360 video.
- Output: Flat (rectilinear) video.
- Animation: Keyframes are converted into FFmpeg expression strings (e.g., `'lerp(0, 45, (t-0)/5)'`) to animate the filter parameters smoothly.

## API

### `POST /video/360/render`
- Input: `Render360Request` (asset_id, path_id or inline path, simple render parameters).
- Output: `Render360Response` (new asset_id/artifact_id).

## Future Work
- Horizon leveling (auto-pitch correction).
- Advanced projection types (little planet, etc.).
