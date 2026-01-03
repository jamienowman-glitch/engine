# AN-01: Quick Start Deployment Guide

## TL;DR - 5 Minute Setup

### Step 1: Choose Your Backend

**Firestore (GCP recommended):**
```bash
curl -X POST http://localhost:5000/routing/routes \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_system" \
  -H "X-Mode: system" \
  -H "X-Project-ID: proj-system" \
  -d '{
    "resource_kind": "analytics_store",
    "tenant_id": "t_system",
    "env": "staging",
    "backend_type": "firestore",
    "config": {
      "project_id": "YOUR_GCP_PROJECT",
      "collection_path": "analytics_store",
      "use_emulator": false
    },
    "required": true
  }'
```

**DynamoDB (AWS):**
```bash
curl -X POST http://localhost:5000/routing/routes \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_system" \
  -H "X-Mode: system" \
  -H "X-Project-ID: proj-system" \
  -d '{
    "resource_kind": "analytics_store",
    "tenant_id": "t_system",
    "env": "staging",
    "backend_type": "dynamodb",
    "config": {
      "region": "us-east-1",
      "table_name": "analytics-store-staging",
      "use_local": false
    },
    "required": true
  }'
```

**Cosmos (Azure):**
```bash
curl -X POST http://localhost:5000/routing/routes \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_system" \
  -H "X-Mode: system" \
  -H "X-Project-ID: proj-system" \
  -d '{
    "resource_kind": "analytics_store",
    "tenant_id": "t_system",
    "env": "staging",
    "backend_type": "cosmos",
    "config": {
      "endpoint": "https://YOUR_ACCOUNT.documents.azure.com:443/",
      "key": "YOUR_KEY",
      "database_id": "analytics_db",
      "container_id": "analytics_store"
    },
    "required": true
  }'
```

### Step 2: Verify Route Created

```bash
curl http://localhost:5000/routing/routes?resource_kind=analytics_store \
  -H "X-Tenant-ID: t_system" \
  -H "X-Mode: system"
```

Should return:
```json
{
  "routes": [
    {
      "id": "...",
      "resource_kind": "analytics_store",
      "backend_type": "firestore",
      ...
    }
  ]
}
```

### Step 3: Restart Service

```bash
# Docker
docker-compose restart northstar-engines

# Kubernetes
kubectl rollout restart deployment/northstar-engines -n staging
```

### Step 4: Test It Works

```bash
curl -X POST http://localhost:5000/analytics/ingest \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_system" \
  -H "X-Mode: system" \
  -H "X-Project-ID: proj-system" \
  -d '{
    "event_type": "test",
    "payload": {},
    "utm_source": "test"
  }'
```

Should return:
```json
{
  "event_id": "req-..."
}
```

---

## Troubleshooting

### Error: `analytics_store.missing_route` (503)

**Cause:** Route not configured
**Fix:** Run Step 1 above (create routing entry)

### Error: Backend connection failed (500)

**Cause:** Credentials wrong or service unavailable
**Fix:** 
- **Firestore:** Check `GOOGLE_APPLICATION_CREDENTIALS` env var
- **DynamoDB:** Check `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- **Cosmos:** Check endpoint and key in config

### Error: Route created but still getting 503

**Cause:** Service hasn't reloaded config
**Fix:** Restart service (Step 3)

---

## What's Actually Deployed?

- ✅ Routing-only analytics store (no in-memory fallback)
- ✅ HTTP 503 if route missing (no silent failures)
- ✅ Support for Firestore, DynamoDB, Cosmos
- ✅ Attribution field tracking (utm_*, dimensional)
- ✅ Query & aggregation endpoints
- ✅ GDPR-compliant delete operations

---

## What's NOT Deployed (Yet)

- 🟡 Agents analytics integration (needs agents update)
- 🟡 UI analytics integration (needs UI update)
- 🟡 Real-time analytics dashboard (future feature)
- 🟡 Advanced filtering/segmentation (future feature)

---

## Next: Tell Agents & UI

Once deployed, update agents and UI to emit events:

```python
# Example: POST /analytics/ingest
requests.post(
    "http://engines:5000/analytics/ingest",
    json={
        "event_type": "agent_execution_started",
        "payload": {"agent_id": "ag-123"},
        "utm_source": "agent_platform",
        "utm_campaign": "q4_2025",
    },
    headers={
        "X-Tenant-ID": "t_system",
        "X-Mode": "system",
        "X-Project-ID": "proj-123",
    }
)
```

---

## Support

For issues:
1. Check logs: `docker-compose logs northstar-engines | grep analytics`
2. Verify route: `curl http://localhost:5000/routing/routes?resource_kind=analytics_store`
3. Restart service: `docker-compose restart northstar-engines`
4. Check documentation: `AN-01_DEPLOYMENT_REPORT.md`

---

**Deployment Status: ✅ READY**

Estimated time: 5-10 minutes  
Risk: Low  
Rollback: Delete route, restart service
