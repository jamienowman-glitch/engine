# Phase 7: Multi-Cam / Audio Sync v1

## Overview
This phase enables the synchronization of multiple video angles (clips) based on their audio tracks. This is achieved by calculating the time offset (lag) between a "master" clip and other "angle" clips using audio cross-correlation.

## Core Concepts

### Multicam Group
A collection of aligned `MediaAsset`s, representing different angles of the same event.
Alignment is stored as `sync_offset_ms` on each angle (relative to the group's zero-point, usually the master's start).

### Audio Sync (Alignment)
The process of extracting audio from video clips and using signal processing (cross-correlation) to find the point of maximum similarity, which corresponds to the time shift needed to align them.

## Architecture

### `engines/align`
- **Responsibility**: Pure signal processing / math.
- **Service**: `AlignService`
    - `calculate_offset(master_audio_path, angle_audio_path) -> float (ms)`
    - Uses `numpy` (if avl) or simple peak finding. For V1, we may mock or use a stub if heavy deps are missing.

### `engines/video_multicam`
- **Responsibility**: Orchestration and CRUD.
- **Models**: `MulticamGroup`, `MulticamAngle`.
- **Service**:
    - `create_group`: Create a new group.
    - `add_angle`: Add an asset to a group.
    - `sync_group`: 
        1. Identify master (first or explicit).
        2. For each other angle, download audio.
        3. Call `align.calculate_offset`.
        4. Update `MulticamAngle.sync_offset_ms`.
- **Routes**:
    - `POST /video/multicam/groups`
    - `POST /video/multicam/groups/{id}/sync`

## API
- `POST /video/multicam/groups/{id}/sync`: Triggers the sync process. Returns the updated group with offsets.

## Integration
- **Timeline**: When adding a multicam angle to the timeline, the `sync_offset_ms` is used to adjust `start_ms_on_timeline` or `in_ms` to maintain sync.
