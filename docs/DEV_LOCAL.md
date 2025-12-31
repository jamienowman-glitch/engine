## Dev Local Runbook (no runtime code changes)

These scripts start the Firestore emulator, seed routing/identity data, and run the FastAPI app on `:8010`.

### One-time
```bash
brew install openjdk@21
brew link --force --overwrite openjdk@21   # or: brew install --cask temurin@21
gcloud components install cloud-firestore-emulator -q
python3 -m pip install uvicorn
```

### Start
```bash
./scripts/dev_local_run.sh
```

What it does:
- Exports env from `scripts/dev_local_env.sh`
- Starts Firestore emulator on `localhost:8900`
- Seeds routing registry + identity defaults for tenant `t_system` / project `p_system`
- Runs `uvicorn engines.chat.service.server:app --host 0.0.0.0 --port 8010` with health checks

### Verify
In another shell:
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8010/ops/status
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8010/api/auth/ticket \
  -H "Authorization: Bearer DEV" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"t_system","mode":"lab","project_id":"p_system","request_id":"req_dev"}'
```

### Notes
- Adjust `scripts/dev_local_env.sh` if you prefer different ports or directories (defaults live under `~/.northstar`).
- Redis is optional for simple status/ticket calls; the chat bus route is pre-configured for `redis://localhost:6379` if you run one.***
