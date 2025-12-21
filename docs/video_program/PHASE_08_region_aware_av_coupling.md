# Phase 8: Region-Aware Audio-Visual Coupling (Focus Automation)

## Overview
This phase links `audio_semantic_timeline` (speech detection) with `video_visual_meta` (region of interest / face detection) to generate automated pan/crop curves ("Focus Automation"). The goal is to dynamically re-frame the video to focus on the speaker during speech segments.

## Core Concepts

### Focus Automation
A set of keyframes (automation curve) for the `crop` filter or `transform` effect that centers a specific region of interest (ROI) over time.

### Audio-Visual Join
- **Input 1**: Semantic Audio Events (Schema: `{start_ms, end_ms, type='speech', speaker_id}`).
- **Input 2**: Visual Metadata (Schema: `{timestamp_ms, regions=[{x, y, w, h, label='face', confidence}]}`).
- **Logic**: For each speech segment, identifying the consistent visual region (face) and generating properties (x, y, zoom) to frame it.

## Architecture

### `engines/video_focus_automation`
- **Responsibility**: Pure logic / geometry engine.
- **Service**: `FocusAutomationService`
    - `generate_focus_curve(audio_events, visual_meta, target_aspect_ratio) -> AutomationTrack`
    - Validation: Ensure smooth transitions (no jump cuts unless specified).

### Integration
- **Inputs**: Requires existing artifacts from `audio_semantic_timeline` and `video_visual_meta`.
- **Outputs**: `AutomationTrack` or `Clip` metadata updates compatible with `video_timeline` and `video_render`.

## API
- `POST /video/focus/generate`: Accepts artifact IDs (audio_semantic, visual_meta), returns automation payload.

## Verification
- **Test**: Synthetic audio events + Synthetic visual regions -> Check generated X/Y curve stays within bounds and tracks the "face".
