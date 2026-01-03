# Azure Cosmos DB Configuration for Analytics Store (AN-01)

Complete instructions for configuring analytics_store routing to Azure Cosmos DB.

---

## Quick Start (Automated)

### Option 1: Using Bash Script (macOS/Linux)

```bash
# Set your Cosmos DB connection string
export AZURE_COSMOS_CONNECTION_STRING="AccountEndpoint=https://your-account.documents.azure.com:443/;AccountKey=your-key==;"

# Run configuration script
cd /Users/jaynowman/dev/northstar-engines
./scripts/configure_azure_analytics.sh
```

The script will:
1. ✓ Verify Cosmos DB credentials
2. ✓ Check engines service is running
3. ✓ Create routing entry
4. ✓ Verify route is active
5. ✓ Test analytics ingest
6. ✓ Test analytics query

### Option 2: Manual Configuration

If the script isn't available, follow the manual steps below.

---

## Manual Configuration

### Step 1: Ensure Engines Service is Running

```bash
cd /Users/jaynowman/dev/northstar-engines
python3 -m engines.app
```

Verify it's running:
```bash
curl http://localhost:5000/health
```

### Step 2: Create Routing Entry

```bash
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
      "throughput": 400,
      "consistency_level": "eventual"
    },
    "modes": ["saas", "enterprise", "system"],
    "priority": 100,
    "metadata": {
      "description": "Analytics store routed to Azure Cosmos DB",
      "created_by": "admin",
      "environment": "production",
      "backend_region": "eastus"
    }
  }'
```

**Expected Response:**
```json
{
  "route_id": "route_xyz123",
  "resource_kind": "analytics_store",
  "backend_type": "cosmos",
  "status": "active",
  "created_at": "2026-01-03T07:35:00Z"
}
```

### Step 3: Verify Route is Active

```bash
curl http://localhost:5000/routing/routes?resource_kind=analytics_store \
  -H "X-Tenant-ID: t_system" \
  -H "X-Mode: system" \
  -H "X-Project-ID: proj-system"
```

You should see the Cosmos DB route listed with `"backend_type": "cosmos"`.

### Step 4: Test Analytics Ingest

```bash
curl -X POST http://localhost:5000/analytics/ingest \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_azure_test" \
  -H "X-Mode: saas" \
  -H "X-Project-ID: proj-azure" \
  -H "X-User-ID: user-infra" \
  -H "X-Surface-ID: cli" \
  -d '{
    "event_type": "azure_config_test",
    "payload": {
      "test": true,
      "backend": "cosmos",
      "region": "eastus"
    },
    "utm_source": "infrastructure",
    "utm_medium": "config",
    "utm_campaign": "azure-setup",
    "app": "engines",
    "platform": "cloud"
  }'
```

**Expected Response:**
```json
{
  "event_id": "evt_abc123def456",
  "tenant_id": "t_azure_test",
  "event_type": "azure_config_test",
  "timestamp": "2026-01-03T07:35:00.123Z",
  "status": "ingested"
}
```

### Step 5: Test Analytics Query

```bash
curl http://localhost:5000/analytics/query \
  -H "X-Tenant-ID: t_azure_test" \
  -H "X-Mode: saas" \
  -H "X-Project-ID: proj-azure" \
  -H "X-User-ID: user-infra" \
  -G \
  --data-urlencode "event_type=azure_config_test" \
  --data-urlencode "time_range=1h"
```

**Expected Response:**
```json
{
  "query": {
    "event_type": "azure_config_test",
    "time_range": "1h",
    "tenant_id": "t_azure_test"
  },
  "results": {
    "total_events": 1,
    "events": [
      {
        "event_id": "evt_abc123def456",
        "event_type": "azure_config_test",
        "timestamp": "2026-01-03T07:35:00.123Z",
        "utm_source": "infrastructure",
        "app": "engines"
      }
    ]
  }
}
```

---

## Cosmos DB Setup Prerequisites

### Create Cosmos DB Account (Azure Portal)

1. **Azure Portal** → Create Resource
2. **Azure Cosmos DB** → Create
3. **Resource Group:** Select or create
4. **Account Name:** `northstar-analytics` (or your choice)
5. **API:** SQL
6. **Capacity Mode:** Provisioned (400 RU/s recommended for testing)
7. **Region:** East US (or your region)
8. **Click Create**

### Create Database & Container

1. **Data Explorer** → New Container
2. **Database ID:** `analytics`
3. **Container ID:** `events`
4. **Partition Key:** `/tenant_id`
5. **Throughput:** 400 RU/s
6. **Click OK**

### Get Connection String

1. **Settings** → Keys
2. **Copy Primary Connection String**
3. Set environment variable:
   ```bash
   export AZURE_COSMOS_CONNECTION_STRING="<paste_here>"
   ```

---

## Configuration Options

### Throughput Scaling

For higher volumes, increase throughput in the route config:

```json
{
  "config": {
    "throughput": 10000
  }
}
```

### Consistency Levels

Adjust consistency level based on requirements:

- `strong` - Highest consistency, lowest throughput
- `bounded_staleness` - Balanced
- `session` - Default (recommended)
- `consistent_prefix` - Higher throughput
- `eventual` - Highest throughput, eventual consistency

### Retention Policy (TTL)

Add automatic document expiration:

```json
{
  "config": {
    "ttl_enabled": true,
    "ttl_seconds": 7776000
  }
}
```

---

## Verification Checklist

After configuration:

- [ ] Route created (HTTP 200)
- [ ] Route listed in `/routing/routes`
- [ ] Ingest returns event ID (HTTP 200)
- [ ] Query returns ingested events
- [ ] Events visible in Azure Portal → Cosmos DB → Data Explorer
- [ ] No HTTP 503 errors on ingest

### Verify in Azure Portal

1. **Azure Portal** → Cosmos DB Account
2. **Data Explorer** → analytics → events
3. **Click Items**
4. See ingested events with your data

---

## Troubleshooting

### Connection String Errors

```
Error: Invalid connection string
```

**Solution:** Verify connection string format:
```
AccountEndpoint=https://<account>.documents.azure.com:443/;AccountKey=<key>==;
```

### Authentication Errors (HTTP 401)

```
Error: Unauthorized - Account not found
```

**Solution:**
1. Verify `AZURE_COSMOS_CONNECTION_STRING` is set
2. Check connection string is from correct Cosmos DB account
3. Verify connection string hasn't expired

### Database Not Found (HTTP 404)

```
Error: Database 'analytics' not found
```

**Solution:**
1. Create database `analytics` in Cosmos DB
2. Create container `events` with partition key `/tenant_id`
3. Update route config with correct database/container names

### Throughput Exceeded (HTTP 429)

```
Error: Throughput limit exceeded
```

**Solution:** Increase throughput in Azure Portal or route config:
```json
{
  "throughput": 1000
}
```

### Missing Partition Key

```
Error: Document must have a value for the partition key property
```

**Solution:** Ensure `tenant_id` is in every analytics event. Service automatically includes it from headers.

---

## Monitoring

### View Metrics in Azure Portal

1. **Cosmos DB Account** → Metrics
2. **Namespace:** Cosmos DB standard metrics
3. Monitor:
   - **Request Units (RU) Consumed**
   - **Data Stored**
   - **Indexed Data Size**
   - **Provisioned Throughput**

### Query with Azure Cosmos Explorer

1. **Data Explorer** → New SQL Query
2. Query ingested events:
   ```sql
   SELECT * FROM events e WHERE e.tenant_id = "t_azure_test"
   ```

### Stream Logs

```bash
docker-compose logs -f northstar-engines | grep analytics
```

---

## Multi-Tenant Setup

Configure different Cosmos accounts per tenant:

```bash
# Tenant A - Cosmos Account 1
curl -X POST http://localhost:5000/routing/routes \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_system" \
  -d '{
    "resource_kind": "analytics_store",
    "backend_type": "cosmos",
    "tenant_id": "t_a",
    "config": {
      "account_name": "northstar-analytics-a",
      "database_id": "analytics",
      "container_id": "events"
    }
  }'

# Tenant B - Cosmos Account 2
curl -X POST http://localhost:5000/routing/routes \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_system" \
  -d '{
    "resource_kind": "analytics_store",
    "backend_type": "cosmos",
    "tenant_id": "t_b",
    "config": {
      "account_name": "northstar-analytics-b",
      "database_id": "analytics",
      "container_id": "events"
    }
  }'
```

---

## Performance Tuning

### Batch Ingest

For high-volume events, batch multiple events:

```bash
curl -X POST http://localhost:5000/analytics/ingest/batch \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_azure_test" \
  -H "X-Mode: saas" \
  -d '[
    {"event_type": "event1", "payload": {...}},
    {"event_type": "event2", "payload": {...}},
    {"event_type": "event3", "payload": {...}}
  ]'
```

### Optimize Query

Use time ranges to limit scans:

```bash
curl http://localhost:5000/analytics/query \
  -H "X-Tenant-ID: t_azure_test" \
  -G \
  --data-urlencode "event_type=azure_config_test" \
  --data-urlencode "time_range=24h" \
  --data-urlencode "filters={\"utm_source\":\"infrastructure\"}"
```

---

## Integration with Other Domains

After configuring analytics_store, you can now configure parallel domains:

- **SEO-01** - SEO config durability (also via Cosmos or different backend)
- **BUD-01** - Budget/usage tracking
- **AUD-01** - Audit sink (append-only)
- **SAVE-01** - Flow/graph/overlay persistence
- **DIAG-01** - Diagnostics endpoint

Each can use same or different Cosmos account.

---

## See Also

- [ANALYTICS_STORE_ROUTING_GUIDE.md](ANALYTICS_STORE_ROUTING_GUIDE.md) - Full routing guide for all backends
- [AN-01_COMPLETE_PACKAGE.md](../../AN-01_COMPLETE_PACKAGE.md) - Comprehensive implementation
- [engines/analytics/routes.py](../../engines/analytics/routes.py) - API implementation
- Azure Cosmos DB Documentation: https://learn.microsoft.com/azure/cosmos-db/

---

## Support

If you encounter issues:

1. Check **Troubleshooting** section above
2. Review engines service logs: `tail -f /tmp/engines.log`
3. Verify connection string in Azure Portal → Keys
4. Check Data Explorer to see if events are stored
5. Run script again with `--verbose` flag

```bash
./scripts/configure_azure_analytics.sh --verbose
```
