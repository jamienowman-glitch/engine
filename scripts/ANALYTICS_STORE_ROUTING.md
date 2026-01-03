# Analytics Store Routing Configuration

This directory contains routing configuration templates for the analytics_store service.

## Quick Setup

1. **Choose your backend** from the options below
2. **Copy the appropriate template** and fill in YOUR credentials
3. **Post the route** via curl or your routing API client
4. **Verify** the route is live
5. **Restart** the engines service

## Backend Options

### Option A: Firestore (GCP)

```json
{
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
}
```

**Requirements:**
- GCP project with Firestore enabled
- Service account with Firestore read/write permissions
- Environment variable: `GOOGLE_APPLICATION_CREDENTIALS`

**Pros:**
- ✅ Native Firestore scalability
- ✅ Real-time listeners available
- ✅ Fine-grained access control

**Cons:**
- Requires GCP account

---

### Option B: DynamoDB (AWS)

```json
{
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
}
```

**Requirements:**
- AWS account with DynamoDB access
- IAM credentials with DynamoDB table permissions
- Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

**Pros:**
- ✅ Serverless scaling
- ✅ Pay-per-request pricing
- ✅ Strong consistency available

**Cons:**
- Requires AWS account

---

### Option C: Cosmos DB (Azure)

```json
{
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
}
```

**Requirements:**
- Azure account with Cosmos DB instance
- Cosmos DB endpoint and master key
- Inline config or environment variables

**Pros:**
- ✅ Multi-region replication
- ✅ Global distribution
- ✅ Multiple consistency models

**Cons:**
- Requires Azure account

---

## Deployment Steps

### 1. Create routing entry

**Via curl (recommended):**

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

**Via Python:**

```python
import requests

route_config = {
    "resource_kind": "analytics_store",
    "tenant_id": "t_system",
    "env": "staging",
    "backend_type": "firestore",
    "config": {
        "project_id": "YOUR_GCP_PROJECT",
        "collection_path": "analytics_store",
        "use_emulator": False,
    },
    "required": True,
}

headers = {
    "X-Tenant-ID": "t_system",
    "X-Mode": "system",
    "X-Project-ID": "proj-system",
}

response = requests.post(
    "http://localhost:5000/routing/routes",
    json=route_config,
    headers=headers,
)

print(response.json())
```

### 2. Verify route is live

```bash
curl http://localhost:5000/routing/routes?resource_kind=analytics_store \
  -H "X-Tenant-ID: t_system" \
  -H "X-Mode: system"
```

Expected response:
```json
{
  "routes": [
    {
      "id": "route-uuid",
      "resource_kind": "analytics_store",
      "tenant_id": "t_system",
      "env": "staging",
      "backend_type": "firestore",
      "config": {...},
      "created_at": "2025-01-02T...",
      "updated_at": "2025-01-02T..."
    }
  ]
}
```

### 3. Restart engines service

```bash
# Docker Compose
docker-compose restart northstar-engines

# Or Kubernetes
kubectl rollout restart deployment/northstar-engines -n staging
```

### 4. Run smoke test

```bash
curl -X POST http://localhost:5000/analytics/ingest \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_system" \
  -H "X-Mode: system" \
  -H "X-Project-ID: proj-system" \
  -d '{
    "event_type": "deployment_test",
    "payload": {"message": "Analytics store is working!"},
    "utm_source": "deployment",
    "app": "northstar_engines"
  }'
```

**Expected response (route configured):**
```json
{
  "event_id": "evt-abc123..."
}
```

**If route not configured:**
```json
{
  "error_code": "analytics_store.missing_route",
  "message": "No analytics_store route configured for tenant=..., env=..., mode=... Configure via /routing/routes..."
}
```
(HTTP 503)

---

## Verification Checklist

- [ ] Backend credentials configured (env vars or config)
- [ ] Routing entry created via POST /routing/routes
- [ ] Route verified live via GET /routing/routes?resource_kind=analytics_store
- [ ] Engines service restarted
- [ ] Smoke test returns 200 with event_id
- [ ] Can query events: GET /analytics/query

---

## Troubleshooting

### Missing Route Error (503)

If you get `analytics_store.missing_route` error:

1. Verify route exists: `curl http://localhost:5000/routing/routes?resource_kind=analytics_store`
2. If not listed, create it (see Deployment Steps #1)
3. If listed but still 503, restart engines service: `docker-compose restart northstar-engines`

### Backend Connection Error (500)

If you get backend-specific errors (500):

1. **Firestore:** Verify `GOOGLE_APPLICATION_CREDENTIALS` env var points to valid JSON keyfile
2. **DynamoDB:** Verify `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` are set; check IAM permissions
3. **Cosmos:** Verify endpoint and key are correct; check firewall rules

Check logs:
```bash
docker-compose logs northstar-engines | grep analytics
```

---

## Next Steps

After successful deployment to staging:

1. **Update Agents** to emit `/analytics/ingest` calls with `utm_source`, `utm_campaign`
2. **Update UI** to emit `/analytics/ingest` calls with `surface`, `app`, `platform`
3. **Monitor** analytics ingest rate and query latency
4. **Deploy to Production** when confident

---

## Related Documentation

- [AN-01 Completion](../AN-01_COMPLETION.md)
- [Routing Registry Docs](../docs/routing/)
- [Analytics API Reference](../engines/analytics/)
