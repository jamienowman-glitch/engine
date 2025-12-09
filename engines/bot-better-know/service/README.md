# BBK Local Service

FastAPI wrapper exposing BBK pipeline operations via HTTP.

## Run

```bash
cd engines/bot-better-know/service
uvicorn server:app --reload --port 8081
```

## Endpoints
- `GET /health` — service check.
- `POST /bbk/upload-and-process` — multipart upload (`file`); saves to `data/uploads/` and runs audio_core pipeline in a run-specific work dir. Writes `run_result.json` under `data/runs/<runId>/`.
- `POST /bbk/start-training` — optional `runId` query/body param; trains LoRA using dataset under that run (or default `data/work_local/dataset`). Writes artifacts under `data/model/<runId>/`.

This service is local-only and CPU-safe; ASR and LoRA fall back to “unavailable” if heavy deps are missing.
