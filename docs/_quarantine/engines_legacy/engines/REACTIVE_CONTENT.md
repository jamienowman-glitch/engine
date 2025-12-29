# Reactive Content Watcher

Planning contract for DatasetEvent-driven reactive plays.

## Trigger types
- Scheduled: cron-style planner jobs (future).
- Chat/on-demand: user/agent triggers via chat surface.
- Reactive: DatasetEvent-driven (focus of this plan).

## Reactive watcher contract
- Input DatasetEvents (examples):
  - `content.published.youtube_video`
  - `content.published.blog`
  - `connector.ingest.article`
- Watcher consumes events and emits follow-ups:
  - `content.reactive.youtube_summary`
  - `content.reactive.seo_snippet`
  - `content.reactive.social_post`
- Event shape (conceptual):
```json
{
  "kind": "content.reactive.youtube_summary",
  "tenantId": "t_dev",
  "env": "dev",
  "source_event": "content.published.youtube_video",
  "refs": ["nexus://snippets/youtube_video_123"],
  "payload": { "video_id": "abc", "title": "Great video", "duration": 480 },
  "trace_id": "trace_123"
}
```
- Watcher lives at `engines/reactive/content/engine.py`; `watch(event)` inspects incoming events and writes new DatasetEvents via logging/Nexus (no token writes).

## Hooks
- Connectors/ingest call watcher after emitting publish events.
- Reactive events are additive: they enqueue work for other clusters; they do not mutate manifests.

## Tests (future)
- YouTube publish → emits `content.reactive.youtube_summary` with refs carried through.
- Unknown event kinds ignored.
- DatasetEvent payload includes source ref/trace and tenant/env passthrough.
