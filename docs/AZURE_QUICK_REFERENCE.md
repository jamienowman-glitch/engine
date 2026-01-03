# Azure Cosmos DB Configuration - Quick Reference

## TL;DR

```bash
# 1. Set your connection string
export AZURE_COSMOS_CONNECTION_STRING="AccountEndpoint=https://your-account.documents.azure.com:443/;AccountKey=your-key==;"

# 2. Start engines service
cd /Users/jaynowman/dev/northstar-engines
python3 -m engines.app

# 3. Run configuration script (in another terminal)
./scripts/configure_azure_analytics.sh

# 4. Done! Events now route to Cosmos DB
```

---

## Manual Commands Only

```bash
# Create route
curl -X POST http://localhost:5000/routing/routes \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_system" \
  -H "X-Mode: system" \
  -H "X-Project-ID: proj-system" \
  -d '{
    "resource_kind": "analytics_store",
    "backend_type": "cosmos",
    "config": {
      "account_name": "northstar-analytics",
      "database_id": "analytics",
      "container_id": "events",
      "partition_key": "/tenant_id",
      "throughput": 400
    },
    "modes": ["saas", "enterprise", "system"],
    "priority": 100
  }'

# Test ingest
curl -X POST http://localhost:5000/analytics/ingest \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_test" \
  -H "X-Mode: saas" \
  -H "X-Project-ID: proj-test" \
  -H "X-User-ID: user1" \
  -H "X-Surface-ID: web" \
  -d '{
    "event_type": "test",
    "payload": {},
    "utm_source": "test"
  }'

# Verify in Cosmos
# Azure Portal → Cosmos DB → Data Explorer → analytics → events → Items
```

---

## Prerequisites Checklist

- [ ] Azure Cosmos DB account created
- [ ] Database `analytics` created
- [ ] Container `events` created (partition key: `/tenant_id`)
- [ ] Connection string copied
- [ ] `AZURE_COSMOS_CONNECTION_STRING` exported
- [ ] Engines service running on port 5000
- [ ] `curl` installed

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success - route created, event ingested |
| 400 | Bad request - check JSON payload |
| 401 | Auth failed - verify connection string |
| 403 | Forbidden - check tenant/mode/project headers |
| 404 | Not found - database/container doesn't exist |
| 429 | Throttled - increase Cosmos throughput |
| 503 | Route missing - create route first |

---

## Key Files

- **Script:** `scripts/configure_azure_analytics.sh`
- **Full Guide:** `docs/AZURE_COSMOS_SETUP.md`
- **Routing Guide:** `docs/engines/ANALYTICS_STORE_ROUTING_GUIDE.md`
- **Implementation:** `engines/analytics/service_reject.py`, `engines/analytics/routes.py`

---

## Next Steps

After Azure is configured:

1. ✅ **AN-01 Complete** - Analytics routing configured
2. 🔄 Start **SEO-01** - SEO config durability
3. 🔄 Start **BUD-01** - Budget/usage tracking
4. 🔄 Start **AUD-01** - Audit sink
5. 🔄 Start **SAVE-01** - Flow/graph persistence
6. 🔄 Start **DIAG-01** - Diagnostics endpoint

All can run in parallel! 🚀
