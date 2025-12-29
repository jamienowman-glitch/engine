# Phase 6: Text & Titles / Variable Fonts v1

## Overview
This phase introduces a dedicated engine `video_text` for rendering text strings into transparent PNG images. These images can be used as overlays in the video timeline. The engine supports variable font settings (weight, width, etc.) where supported by the underlying font file.

## Core Concepts

### Text Assets
Text is rendered into a standard `MediaAsset` of kind `image`. This integration allows text overlays to be treated exactly like any other image clip in the timeline (scaling, positioning, opacity, etc.).

### Variable Fonts
The engine accepts a `variation_settings` dictionary to drive variable font axes (e.g., `{'wght': 700, 'wdth': 100}`).

## Architecture

### `engines/video_text`
- **Models**:
    - `TextRenderRequest`: Text content, styling (font, size, color), layout (width/height), and variation settings.
    - `TextRenderResponse`: Returns the ID of the created asset.
- **Service**:
    - Uses **PIL (Pillow)** to render text to an RGBA image.
    - Uploads the resulting PNG via `MediaService`.
    - Returns the Asset ID.

## API

### `POST /video/text/render`
- Input: `TextRenderRequest`.
- Output: `TextRenderResponse`.

## Integration
- **Timeline**: Clients place the returned Asset ID on a video track (usually a higher z-order track for overlay).
- **Render**: The `video_render` engine consumes the PNG asset naturally.

## Limitations (V1)
- Static text only (no per-character animation in the asset itself).
- Basic wrapping/layout.
- Raster output (PNG).
