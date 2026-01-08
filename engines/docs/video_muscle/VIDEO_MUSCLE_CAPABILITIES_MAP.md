# Video Muscle Capabilities Map

**Status**: Strong Foundation (Backend). UI Lagging.
**Architecture**: `TimelineService` (State) -> `RenderService` (Processing).

## 1. Core Muscles

### A. Video Timeline (`engines/muscle/video_timeline`)
**Type**: State Machine (CRUD)
**Capabilities**:
- **Project Structure**: Project -> Sequence -> Track -> Clip.
- **Editing**: Trim, Split, Move, Ripple.
- **Effects**: Filter Stacks (LUTs, EQ, Blur), Parameter Automation (Keyframes).
- **Transitions**: Standard dissolve/wipe logic.
- **Integrations**: "Promote Multicam", "Ingest Assist Highlights".

### B. Video Render (`engines/muscle/video_render`)
**Type**: Heavy Processor (Async Jobs)
**Capabilities**:
- **Engine**: FFmpeg + Hardware Acceleration (NVENC/VideoToolbox).
- **Format**: Multi-profile support (Social 1080p, 4K, Proxies).
- **Smart Filters**: Optical Flow Slowmo, VidStab Stabilization, Color Grading.
- **Audio**: Ducking (Speech detection), Voice Polish integration.
- **Execution**: Chunked parallel rendering + Stitching.

### C. Specialized Helpers
- **Video Text** (`engines/muscle/video_text`): Text overlay generation (likely SVG/Image generation for burn-in).
- **Video Mask** (`engines/muscle/video_mask`): AI segmentation / Matte generation.
- **Video Multicam** (`engines/muscle/video_multicam`): Audio-based alignment of multiple angles.

## 2. Gaps vs CapCut (Baseline)

| Feature | Status | Notes |
| :--- | :--- | :--- |
| **Multi-Track Editing** | ✅ | Full support in data model. |
| **Smart Captions** | ⚠️ | "Burn-in" supported, but editable text logic seems separate (`video_text`). |
| **Stickers/Overlays** | ❌ | No specific "Sticker" track type or asset kind explicit in recon. |
| **Speed Ramping** | ✅ | Optical flow and speed property exist. |
| **Keyframing** | ✅ | `ParameterAutomation` supports standard keyframes. |

## 3. Gaps vs Premiere (Pro)

| Feature | Status | Notes |
| :--- | :--- | :--- |
| **Bin/Media Mgmt** | ❌ | Relies on `media_v2`. No concept of "Bins" in Project. |
| **Color Wheels** | ⚠️ | Filter stack exists, but "Grading Panel" API is likely custom filters. |
| **Plug-ins (VST/OFX)** | ❌ | Closed ecosystem. |
| **Nested Seqs** | 🤷‍♂️ | Data model allows Sequence, but using Sequence as Clip? Not seen. |
