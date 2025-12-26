
# Timeline Examples

## Scenario: YouTube Vlog Edit

This example demonstrates a complete timeline structure for a typical vlog with:
1. Main A-Roll track (Multicam promoted).
2. B-Roll track (Assist highlights).
3. Background Music track.
4. Focus Automation (Pan/Scan) on A-Roll.

### 1. Project & Sequence
**Sequence Structure**
```json
{
  "id": "seq_01",
  "project_id": "proj_vlog_01",
  "name": "Main Edit",
  "fps": 30.0,
  "tenant_id": "demo_tenant"
}
```

### 2. Track Layout
**Track 1: Main Video (A-Roll)**
```json
{
  "id": "track_main",
  "sequence_id": "seq_01",
  "kind": "video",
  "video_role": "main",
  "order": 0
}
```

**Track 2: B-Roll (Generic/Assist)**
```json
{
  "id": "track_broll",
  "sequence_id": "seq_01",
  "kind": "video",
  "video_role": "b-roll",
  "order": 1
}
```

**Track 3: Music**
```json
{
  "id": "track_music",
  "sequence_id": "seq_01",
  "kind": "audio",
  "audio_role": "music",
  "order": 2
}
```

### 3. Clips & Automation

**Clip: Intro A-Roll (with Focus Automation)**
```json
{
  "id": "clip_a_01",
  "track_id": "track_main",
  "asset_id": "asset_camera_01",
  "in_ms": 0,
  "out_ms": 5000,
  "start_ms_on_timeline": 0,
  "alignment_applied": true,
  "meta": {"source": "multicam_auto_nav"}
}
```

**Automation: Digital Pan/Zoom on Intro**
```json
[
  {
    "target_id": "clip_a_01",
    "property": "scale",
    "keyframes": [
      {"time_ms": 0, "value": 1.0},
      {"time_ms": 4000, "value": 1.2}
    ]
  },
  {
    "target_id": "clip_a_01",
    "property": "crop_x",
    "keyframes": [
      {"time_ms": 0, "value": 0.5},
      {"time_ms": 4000, "value": 0.6}
    ]
  }
]
```

**Clip: B-Roll Cutaway**
```json
{
  "id": "clip_b_01",
  "track_id": "track_broll",
  "asset_id": "asset_stock_broll",
  "in_ms": 2000,
  "out_ms": 4000,
  "start_ms_on_timeline": 1500,
  "meta": {"source": "assist_highlight", "score": 0.95}
}
```

### 4. Operations Usage

**Trim A-Roll (Ripple)**
`POST /video/clips/clip_a_01/trim`
```json
{
  "new_in_ms": 500,
  "new_out_ms": 4500,
  "ripple": true
}
```

**Promote Multicam**
`POST /video/projects/proj_vlog_01/multicam/promote`
```json
{
  "name": "Multicam Seq",
  "result": {
    "tenant_id": "demo_tenant",
    "env": "dev",
    "cuts": [
      {"asset_id": "cam_a", "start_ms": 0, "end_ms": 2000},
      {"asset_id": "cam_b", "start_ms": 2000, "end_ms": 5000}
    ]
  }
}
```
