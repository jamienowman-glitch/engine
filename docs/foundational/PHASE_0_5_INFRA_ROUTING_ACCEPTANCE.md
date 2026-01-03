# Phase 0.5 — Infra Routing Acceptance

Prereqs: routing registry endpoints available; surface normalization helper deployed (aliases: squared/squared2/SQUARED2/SQUARED² → canonical); cloud creds for sellable modes; filesystem allowed only in lab.

## Registry operations (resource_kind example: object_store)
```bash
curl -X POST http://localhost:8010/routing/routes \
  -H 'Content-Type: application/json' \
  -d '{"resource_kind":"object_store","tenant_id":"t_demo","env":"dev","backend_type":"filesystem","config":{"base_dir":"var/object_store"},"required":true}'
curl "http://localhost:8010/routing/routes?resource_kind=object_store&tenant_id=t_demo&env=dev"
```
Expect route persisted; restart server and GET returns same. For sellable modes (saas/enterprise/t_system) routes pointing to filesystem/in_memory should be rejected with explicit error.

Audit/Stream: check logs or timeline for audit event on upsert (action=routing.upsert, includes resource_kind, tenant/mode/env/project/app/surface if provided).

Alias test: upsert with surface=SQUARED² header, list with surface=squared returns same route.

## Filesystem adapter proofs (lab-only)
- object_store: write/read blob
```bash
echo "hello" > /tmp/obj.txt
curl -X POST http://localhost:8010/media/upload -F file=@/tmp/obj.txt -H 'X-Tenant-Id: t_demo' -H 'X-Mode: saas'
ls var/object_store  # file exists
```
- Verify same call with X-Mode: lab succeeds when route -> filesystem; with X-Mode: saas fails (forbidden backend class).
- event_stream: after setting route to filesystem, send chat/canvas events; restart; SSE/WS replay returns past events; files present under var/event_stream/...
- tabular_store: write policy record via associated service; verify JSONL/SQLite file exists under var/tabular/...
- metrics_store: POST raw KPI (per KPI acceptance); verify var/metrics/... file.
- memory_store: use /memory endpoints; verify var/memory/... files.

## Env removal check
Unset related env vars (e.g., CHAT_BUS_BACKEND, STREAM_TIMELINE_BACKEND, STORAGE_BUCKET); routes still function via registry-configured backends (filesystem in lab, cloud in sellable modes).

## S3 backend check (object_store)
Upsert route with backend_type=s3 and config {bucket, region}:
```bash
curl -X POST http://localhost:8010/routing/routes \
  -H 'Content-Type: application/json' \
  -d '{"resource_kind":"object_store","tenant_id":"t_demo","env":"dev","backend_type":"s3","config":{"bucket":"my-bucket","region":"us-east-1"},"required":true}'
# upload/download (replace endpoint per service API)
```
Expect PUT/GET to succeed (or explicit NotImplemented for missing adapter).

## Timeline replay (filesystem event_stream)
1) Route event_stream to filesystem.
2) Send chat/canvas events (or /actions/execute) to append.
3) Restart server.
4) Connect SSE/WS with Last-Event-ID; expect replay.

## Route change audit
Upsert a new route or change backend_type; verify audit + StreamEvent emitted (action=routing.change) with resource_kind and scope.***
