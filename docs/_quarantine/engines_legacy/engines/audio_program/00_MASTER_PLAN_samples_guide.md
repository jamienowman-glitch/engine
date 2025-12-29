# Audio Sample Engines - Guide

This document describes the 5 engines comprising the Audio Sample Spine.

## 1. Audio Hits (`engines/audio_hits`)

detects transients and creates "one-shot" sample artifacts.

**Input (`HitDetectRequest`):**
```json
{
  "tenant_id": "t1",
  "env": "dev",
  "asset_id": "asset_123",
  "min_peak_db": -30.0,
  "pre_roll_ms": 10
}
```

**Output (`HitDetectResult`):**
Returns list of events and new `audio_hit` artifacts.

---

## 2. Audio Loops (`engines/audio_loops`)

Detects stable rhythm sections and creates looping artifacts.

**Input (`LoopDetectRequest`):**
```json
{
  "tenant_id": "t1",
  "asset_id": "asset_123",
  "target_bars": [2, 4],
  "bpm_hint": 120
}
```

**Output (`LoopDetectResult`):**
Returns `audio_loop` artifacts with `bpm` and `loop_bars` metadata.

---

## 3. Audio Voice Phrases (`engines/audio_voice_phrases`)

Slices vocal phrases based on caption timing.

**Input (`VoicePhraseDetectRequest`):**
```json
{
  "tenant_id": "t1",
  "asset_id": "asset_123",
  "max_gap_ms": 500
}
```

**Output (`VoicePhraseDetectResult`):**
Returns `audio_phrase` artifacts with `transcript` metadata.

---

## 4. Sample Library (`engines/audio_sample_library`)

Query layer for discovering samples.

**API:** `GET /audio/sample-library/samples`

**Parameters:**
- `kind`: `audio_hit` | `audio_loop` | `audio_phrase`
- `min_bpm` / `max_bpm`
- `loop_bars`
- `has_transcript`

**Response:**
```json
{
  "samples": [
    {
      "artifact_id": "art_1",
      "kind": "audio_loop",
      "bpm": 120.0,
      "loop_bars": 2,
      "source_start_ms": 1000,
      "source_end_ms": 5000
    }
  ]
}
```

---

## 5. Pipeline (`engines/audio_field_to_samples`)

Run all detectors on an asset.

**Python:**
```python
req = FieldToSamplesRequest(tenant_id="t1", env="dev", asset_id="vid_1")
res = pipeline_service.process_asset(req)
print(res.summary_meta) 
# {'hits_count': 12, 'loops_count': 3, 'phrases_count': 5}
```
