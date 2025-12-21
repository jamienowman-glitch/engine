# Phase 7: Multi-Cam Session Engine v1

## Overview
The `video_multicam` engine manages "Multi-Cam Sessions" — collections of video assets representing different angles of the same performance. It provides capabilities to:
1.  **Align** cameras using audio correlation.
2.  **Sync** tracks onto the timeline.
3.  **Auto-Cut** a program sequence using heuristics.

## Data Models
- **MultiCamSession**: The source of truth for which assets belong together and their time offsets.
- **TrackSpec**: Defines a single camera's role (primary, wide, etc.) and alignment offset.

## Alignment Logic
We extract audio from all cameras and cross-correlate against a "base asset" (usually the Primary camera) to find the temporal offset in milliseconds.

## Auto-Cut Heuristics
V1 is rule-based:
- Switches angles every 1.5s - 6s.
- Prefers Primary camera (60% of time).
- Deterministic random seed based on session ID for consistent re-cuts.

## API
- `POST /video/multicam/sessions` (Create)
- `GET /video/multicam/sessions?tenant_id=...` (List)
- `GET /video/multicam/sessions/{id}` (Get)
- `POST /video/multicam/sessions/{id}/align` (Run alignment)
- `POST /video/multicam/sessions/{id}/build-sequence` (Build synced sequence)
- `POST /video/multicam/sessions/{id}/auto-cut` (Generate program cut)
