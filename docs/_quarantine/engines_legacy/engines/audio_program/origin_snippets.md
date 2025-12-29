# Origin Snippets

Audio-first helper that maps analyzed audio artifacts (hits/loops/phrases) back to source video windows, with optional rendering of those windows.

## Models
- `OriginSnippetBatchRequest`: `{tenant_id, env, user_id?, items:[{audio_artifact_id, padding_ms?, max_duration_ms?}], mode=timeline_only|render_clips, attach_to_project_id?, render_profile?}`
- `OriginSnippet`: `{audio_artifact_id, source_asset_id, source_start_ms, source_end_ms, video_clip_id?, video_artifact_id?, meta}` (meta carries padding/max_duration/op_type/op_version, render info when present)
- `OriginSnippetBatchResult`: `{snippets:[], project_id?, sequence_id?, meta}`

## JSON examples
**Batch request (timeline_only)**:
```json
{
  "tenant_id": "t_demo",
  "env": "dev",
  "user_id": "u1",
  "mode": "timeline_only",
  "items": [
    {"audio_artifact_id": "art_hit_123", "padding_ms": 250, "max_duration_ms": 500}
  ]
}
```

**Batch result**:
```json
{
  "snippets": [
    {
      "audio_artifact_id": "art_hit_123",
      "source_asset_id": "asset_video_9",
      "source_start_ms": 0,
      "source_end_ms": 500,
      "video_clip_id": "clip_ab12",
      "video_artifact_id": null,
      "meta": {
        "padding_ms": 250,
        "max_duration_ms": 500,
        "op_type": "origin_snippets.build_v1",
        "op_version": "v1"
      }
    }
  ],
  "project_id": "proj_origin_01",
  "sequence_id": "seq_origin_01",
  "meta": {"mode": "timeline_only", "track_id": "track_origin"}
}
```

**Batch request (render_clips)**:
```json
{
  "tenant_id": "t_demo",
  "env": "dev",
  "mode": "render_clips",
  "render_profile": "1080p_30_web",
  "items": [
    {"audio_artifact_id": "art_loop_42", "padding_ms": 100}
  ]
}
```

## Modes
- `timeline_only` (default): Build a video_timeline project/sequence (or append via new sequence/track to `attach_to_project_id`) and add clips on an “origin” track using the computed source window (`in_ms/out_ms/start_ms_on_timeline`). No renders are produced; clip IDs returned for downstream edit flows.
- `render_clips`: Create the same timeline grouping, then call `video_render` for each window (profile from request, default `1080p_30_web`). Register `render_snippet` artifacts on the source asset with lineage meta.

## Lineage + provenance
- Each rendered window registers a `render_snippet` artifact on the **source asset** with `upstream_artifact_ids=[audio_artifact_id]`, `source_start_ms/source_end_ms`, `project_id/sequence_id/clip_id`, `render_artifact_id`, `render_asset_id`, and `op_type=origin_snippets.build_v1`.
- Keeps “origin video” links for beat explainers, educational provenance, and future edit automation (selectable clips, render cache keys).

## Guardrails / scope
- Deterministic engine only; no LLM/Nexus/orchestration hooks.
- Tenant/env/user context required via standard RequestContext; no secrets or prompt handling introduced.
- Firearms/Strategy Lock not enforced here (honors existing media/video policies); add TODOs at call sites if future policy demands render gating.
