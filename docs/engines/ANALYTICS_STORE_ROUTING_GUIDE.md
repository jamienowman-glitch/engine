# Analytics Store (AN-01) Routing Configuration Guide

Complete guide for configuring analytics_store routing to real infrastructure backends across all cloud platforms.

---

## Overview

The analytics store is **routing-only** enforced. All analytics data must be persisted to a configured backend:
- **Firestore** (Google Cloud Platform)
- **DynamoDB** (Amazon Web Services)
- **Cosmos DB** (Microsoft Azure)

**Missing route behavior:** HTTP 503 with `error_code: analytics_store.missing_route`

---

## Prerequisites

1. **Running Engines Service**
   ```bash
   docker-compose up -d northstar-engines
   # or: python -m engines.app
   ```

2. **Routing Registry Available**
   ```bash
   curl http://localhost:5000/routing/routes -H "X-Tenant-ID: t_system" -H "X-Mode: system" -H "X-Project-ID: proj-system"
   ```

3. **Cloud Infrastructure Credentials** (configured in environment)

---

## Configuration: Google Cloud Platform (Firestore)

### Prerequisites
- GCP project with Firestore enabled
- Service account key with Firestore read/write permissions
- `GOOGLE_APPLICATION_CREDENTIALS` environment variable set

### Step 1: Create Routing Entry

```bash
curl -X POST http://localhost:5000/routing/routes \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_system" \
  -H "X-Mode: system" \
  -H "X-Project-ID: proj-system" \
  -d '{
    "resource_kind": "analytics_store",
    "backend_type": "firestore",
    "config": {
      "project_id": "YOUR_GCP_PROJECT_ID",
      "database_id": "(default)",
      "collection": "analytics_events"
    },
    "modes": ["saas", "enterprise", "system"],
    "priority": 100,
    "metadata": {
      "description": "Analytics store routed to Firestore",
      "created_by": "admin",
      "environment": "production"
    }
  }'
```

### Step 2: Verify Route is Active

```bash
curl http://localhost:5000/routing/routes?resource_kind=analytics_store \
  -H "X-Tenant-ID: t_system" \
  -H "X-Mode: system" \
  -H "X-Project-ID: proj-system"
```

### Step 3: Test Analytics Ingest

```bash
curl -X POST http://localhost:5000/analytics/ingest \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_customer" \
  -H "X-Mode: saas" \
  -H "X-Project-ID: proj-customer" \
  -H "X-User-ID: user_123" \
  -H "X-Surface-ID: web" \
  -d '{
    "event_type": "page_view",
    "payload": {
      "url": "https://example.com/dashboard",
      "title": "Dashboard"
    },
    "utm_source": "organic",
    "utm_medium": "search",
    "utm_campaign": "analytics-test",
    "app": "customer_app",
    "platform": "web"
  }'
```

**Expected Response:** HTTP 200 with event ID

### Step 4: Query Analytics

```bash
curl http://localhost:5000/analytics/query \
  -H "X-Tenant-ID: t_customer" \
  -H "X-Mode: saas" \
  -H "X-Project-ID: proj-customer" \
  -H "X-User-ID: user_123" \
  -G \
  --data-urlencode "event_type=page_view" \
  --data-urlencode "time_range=24h"
```

---

## Configuration: Amazon Web Services (DynamoDB)

### Prerequisites
- AWS account with DynamoDB enabled
- IAM credentials with DynamoDB read/write permissions
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables set
- `AWS_REGION` environment variable set (e.g., `us-east-1`)

### Step 1: Create Routing Entry

```bash
curl -X POST http://localhost:5000/routing/routes \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_system" \
  -H "X-Mode: system" \
  -H "X-Project-ID: proj-system" \
  -d '{
    "resource_kind": "analytics_store",
    "backend_type": "dynamodb",
    "config": {
      "table_name": "analytics_events",
      "region": "us-east-1",
      "ttl_attribute": "expiration_time",
      "ttl_days": 90
    },
    "modes": ["saas", "enterprise", "system"],
    "priority": 100,
    "metadata": {
      "description": "Analytics store routed to DynamoDB",
      "created_by": "admin",
      "environment": "production"
    }
  }'
```

### Step 2: Verify Route is Active

```bash
curl http://localhost:5000/routing/routes?resource_kind=analytics_store \
  -H "X-Tenant-ID: t_system" \
  -H "X-Mode: system" \
  -H "X-Project-ID: proj-system"
```

### Step 3: Test Analytics Ingest

```bash
curl -X POST http://localhost:5000/analytics/ingest \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_customer" \
  -H "X-Mode: saas" \
  -H "X-Project-ID: proj-customer" \
  -H "X-User-ID: user_123" \
  -H "X-Surface-ID: mobile" \
  -d '{
    "event_type": "button_click",
    "payload": {
      "button_id": "cta_signup",
      "section": "hero"
    },
    "utm_source": "paid",
    "utm_medium": "social",
    "utm_campaign": "aws-test",
    "app": "mobile_app",
    "platform": "ios"
  }'
```

**Expected Response:** HTTP 200 with event ID

### Step 4: Query Analytics

```bash
curl http://localhost:5000/analytics/query \
  -H "X-Tenant-ID: t_customer" \
  -H "X-Mode: saas" \
  -H "X-Project-ID: proj-customer" \
  -H "X-User-ID: user_123" \
  -G \
  --data-urlencode "event_type=button_click" \
  --data-urlencode "time_range=7d"
```

---

## Configuration: Microsoft Azure (Cosmos DB)

### Prerequisites
- Azure subscription with Cosmos DB enabled
- Cosmos DB account created with SQL API
- Cosmos DB connection string (primary or secondary)
- `AZURE_COSMOS_CONNECTION_STRING` environment variable set

### Step 1: Create Routing Entry

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
      "account_name": "your-cosmos-account",
      "database_id": "analytics_db",
      "container_id": "events",
      "partition_key": "/tenant_id",
      "throughput": 400
    },
    "modes": ["saas", "enterprise", "system"],
    "priority": 100,
    "metadata": {
      "description": "Analytics store routed to Cosmos DB",
      "created_by": "admin",
      "environment": "production"
    }
  }'
```

### Step 2: Verify Route is Active

```bash
curl http://localhost:5000/routing/routes?resource_kind=analytics_store \
  -H "X-Tenant-ID: t_system" \
  -H "X-Mode: system" \
  -H "X-Project-ID: proj-system"
```

### Step 3: Test Analytics Ingest

```bash
curl -X POST http://localhost:5000/analytics/ingest \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_customer" \
  -H "X-Mode: saas" \
  -H "X-Project-ID: proj-customer" \
  -H "X-User-ID: user_123" \
  -H "X-Surface-ID: web" \
  -d '{
    "event_type": "form_submission",
    "payload": {
      "form_name": "contact_form",
      "fields_count": 5
    },
    "utm_source": "direct",
    "utm_medium": "email",
    "utm_campaign": "azure-test",
    "app": "web_app",
    "platform": "web"
  }'
```

**Expected Response:** HTTP 200 with event ID

### Step 4: Query Analytics

```bash
curl http://localhost:5000/analytics/query \
  -H "X-Tenant-ID: t_customer" \
  -H "X-Mode: saas" \
  -H "X-Project-ID: proj-customer" \
  -H "X-User-ID: user_123" \
  -G \
  --data-urlencode "event_type=form_submission" \
  --data-urlencode "time_range=30d"
```

---

## Common API Endpoints

### Ingest Analytics Event
```
POST /analytics/ingest
Headers:
  - X-Tenant-ID: t_<tenant_id>
  - X-Mode: saas|enterprise|system|lab
  - X-Project-ID: proj_<project_id>
  - X-User-ID: user_<user_id>
  - X-Surface-ID: <surface_id>

Body:
{
  "event_type": "string (required)",
  "payload": { "key": "value", ... },
  "utm_source": "string (optional)",
  "utm_medium": "string (optional)",
  "utm_campaign": "string (optional)",
  "utm_content": "string (optional)",
  "utm_term": "string (optional)",
  "app": "string (optional)",
  "platform": "string (optional)",
  "surface": "string (optional)"
}
```

### Query Analytics
```
GET /analytics/query
Query Parameters:
  - event_type: string (required)
  - time_range: 24h|7d|30d|90d (optional, default 24h)
  - filters: {"key": "value"} (optional)

Headers:
  - X-Tenant-ID: t_<tenant_id>
  - X-Mode: saas|enterprise|system
  - X-Project-ID: proj_<project_id>
  - X-User-ID: user_<user_id>
```

### Aggregate Analytics
```
GET /analytics/aggregate
Query Parameters:
  - event_type: string (required)
  - aggregate_by: utm_source|utm_medium|app|platform (required)
  - time_range: 24h|7d|30d|90d (optional)

Headers:
  - X-Tenant-ID: t_<tenant_id>
  - X-Mode: saas|enterprise|system
  - X-Project-ID: proj_<project_id>
  - X-User-ID: user_<user_id>
```

### Delete Event (GDPR)
```
DELETE /analytics/event/<event_id>
Headers:
  - X-Tenant-ID: t_<tenant_id>
  - X-Mode: saas|enterprise|system
  - X-Project-ID: proj_<project_id>
  - X-User-ID: user_<user_id>
```

---

## Verification Checklist

After configuration, verify:

- [ ] Route created successfully (HTTP 200)
- [ ] Route appears in `/routing/routes?resource_kind=analytics_store`
- [ ] Ingest request returns HTTP 200 with event ID
- [ ] Query returns events ingested
- [ ] Events visible in cloud backend (Firestore console, DynamoDB, Cosmos DB)
- [ ] Aggregate endpoint returns grouped metrics
- [ ] Delete endpoint removes events

---

## Troubleshooting

### Missing Route Error (HTTP 503)
```
{
  "error_code": "analytics_store.missing_route",
  "message": "No route configured for analytics_store in current mode"
}
```
**Solution:** Create routing entry using steps above

### Authentication Errors
- **Firestore:** Check `GOOGLE_APPLICATION_CREDENTIALS` points to valid service account key
- **DynamoDB:** Check `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` set correctly
- **Cosmos:** Check `AZURE_COSMOS_CONNECTION_STRING` set correctly

### Invalid Tenant ID
```
{
  "error_code": "auth.invalid_tenant",
  "message": "Tenant ID must match pattern ^t_[a-z0-9_-]+$"
}
```
**Solution:** Use tenant IDs like `t_customer`, `t_system`, not `customer` or `test-tenant`

### Route Not Found After Creation
```bash
# Wait a moment for route propagation
sleep 2

# Verify route is listed
curl http://localhost:5000/routing/routes?resource_kind=analytics_store \
  -H "X-Tenant-ID: t_system" \
  -H "X-Mode: system" \
  -H "X-Project-ID: proj-system"
```

---

## Performance Tuning

### Firestore
```json
{
  "config": {
    "batch_size": 500,
    "write_timeout_seconds": 30,
    "read_timeout_seconds": 10
  }
}
```

### DynamoDB
```json
{
  "config": {
    "read_capacity_units": 100,
    "write_capacity_units": 100,
    "batch_write_size": 25
  }
}
```

### Cosmos DB
```json
{
  "config": {
    "throughput": 400,
    "consistency_level": "eventual",
    "max_retries": 3
  }
}
```

---

## Multi-Cloud Setup

To use different backends per tenant:

```bash
# Azure for tenant_a
curl -X POST http://localhost:5000/routing/routes \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_system" \
  -d '{
    "resource_kind": "analytics_store",
    "backend_type": "cosmos",
    "tenant_id": "t_a",
    ...
  }'

# AWS for tenant_b
curl -X POST http://localhost:5000/routing/routes \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_system" \
  -d '{
    "resource_kind": "analytics_store",
    "backend_type": "dynamodb",
    "tenant_id": "t_b",
    ...
  }'

# GCP for tenant_c
curl -X POST http://localhost:5000/routing/routes \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_system" \
  -d '{
    "resource_kind": "analytics_store",
    "backend_type": "firestore",
    "tenant_id": "t_c",
    ...
  }'
```

---

## Environment Variables

Create `.env` file for local testing:

```bash
# Common
ENGINES_PORT=5000
ENGINES_MODE=saas
LOG_LEVEL=debug

# Firestore
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# DynamoDB
AWS_ACCESS_KEY_ID=your_key_id
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# Cosmos DB
AZURE_COSMOS_CONNECTION_STRING=your_connection_string
```

Load before starting:
```bash
set -a
source .env
set +a
docker-compose up -d northstar-engines
```

---

## Monitoring & Logging

### Check Routing Service Health
```bash
curl http://localhost:5000/health
```

### View Recent Routes
```bash
curl http://localhost:5000/routing/routes \
  -H "X-Tenant-ID: t_system" \
  -H "X-Mode: system" \
  -H "X-Project-ID: proj-system" | jq '.'
```

### Stream Logs
```bash
docker-compose logs -f northstar-engines | grep analytics
```

---

## See Also

- [AN-01_COMPLETE_PACKAGE.md](../../AN-01_COMPLETE_PACKAGE.md) - Comprehensive implementation guide
- [QUICKSTART_AN01.md](../../QUICKSTART_AN01.md) - 5-minute setup
- [engines/analytics/service_reject.py](../../engines/analytics/service_reject.py) - Service implementation
- [engines/analytics/routes.py](../../engines/analytics/routes.py) - HTTP endpoints
