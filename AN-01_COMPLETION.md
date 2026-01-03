# AN-01: Analytics Store Enforcement ✅ COMPLETE

**Status:** IMPLEMENTED & VERIFIED  
**Date:** 2025-01-02  
**Preconditions Met:** AUTH-01 (identity/tenant routing)  
**Dependencies Unblocked:** Agents/UI analytics durability features  

---

## Overview

AN-01 enforces **routing-only analytics operations** with hard rejection on missing configuration:

| Mode | Missing Route Behavior |
|------|------------------------|
| **SaaS/Enterprise/System** | HTTP 503 + error_code: `analytics_store.missing_route` |
| **Lab** | Warning logged; continues with None adapter (debug tolerance) |

---

## Implementation Summary

### 1. Service Enforcement (`service_reject.py`)

**File:** `engines/analytics/service_reject.py`

```python
class AnalyticsStoreServiceRejectOnMissing:
    """Analytics store with routing-only enforcement."""
```

**Features:**
- ✅ Routing registry lookup with hard rejection on missing route
- ✅ Lab mode exception (warn-only)
- ✅ Three backend adapters: Firestore, DynamoDB, Cosmos
- ✅ Attribution field support (UTM/SEO metadata)
- ✅ Three operations: ingest, query, aggregate

**Key Method:** `_resolve_adapter_or_reject()`
- Calls `routing_registry().get_route(resource_kind="analytics_store", ...)`
- **SaaS/Enterprise/System modes:** Raises `MissingAnalyticsStoreRoute` (HTTP 503)
- **Lab mode:** Logs warning, returns None (allows continued execution for debugging)

**Exception:** `MissingAnalyticsStoreRoute`
- `error_code: "analytics_store.missing_route"`
- `status_code: 503`
- Client receives: `{"error_code": "analytics_store.missing_route", "message": "..."}`

---

### 2. HTTP Routes (`routes.py`)

**File:** `engines/analytics/routes.py`

**Routes Implemented:**

| Endpoint | Method | Purpose | Response (Success) | Response (Missing Route) |
|----------|--------|---------|-------------------|--------------------------|
| `/analytics/ingest` | POST | Store analytics event | 200 + event_id | 503 |
| `/analytics/query` | GET | Query events by time/filters | 200 + records[] | 503 |
| `/analytics/aggregate` | GET | Aggregate metrics | 200 + aggregated data | 503 |
| `/analytics/event/{event_id}` | DELETE | Delete event (GDPR/purge) | 204 | 503 |

**Request Examples:**

```bash
# Ingest event with attribution
curl -X POST http://localhost:5000/analytics/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "pageview",
    "payload": {"url": "https://example.com/page"},
    "utm_source": "google",
    "utm_campaign": "summer_2025",
    "app": "northstar_ui",
    "surface": "homepage",
    "platform": "web"
  }'

# Query analytics
curl "http://localhost:5000/analytics/query?start_time=2025-01-01T00:00:00Z&utm_source=organic&limit=100"

# Aggregate metrics
curl "http://localhost:5000/analytics/aggregate?metric=pageviews&group_by=utm_source,surface"

# Delete event
curl -X DELETE http://localhost:5000/analytics/event/event-123
```

**Error Handling:**

```json
{
  "error_code": "analytics_store.missing_route",
  "message": "No analytics_store route configured for tenant=..., env=..., mode=... Configure via /routing/routes..."
}
```

---

### 3. Attribution Field Enforcement

**Required/Optional Fields Supported:**

| Field | Type | Purpose |
|-------|------|---------|
| `event_type` | string | Event classification (pageview, cta_click, form_submit) |
| `payload` | dict | Event-specific data (JSON-serializable) |
| `utm_source` | string | Traffic source (google, organic, direct) |
| `utm_medium` | string | Traffic medium (cpc, email, social) |
| `utm_campaign` | string | Campaign identifier |
| `utm_content` | string | Ad variant |
| `utm_term` | string | Keyword |
| `seo_slug` | string | URL slug for SEO tracking |
| `seo_title` | string | Page title |
| `seo_description` | string | Meta description |
| `app` | string | Application identifier |
| `surface` | string | UI surface/page section |
| `platform` | string | Platform (web, mobile, desktop) |
| `session_id` | string | Session identifier for session tracking |

---

### 4. Integration Tests

**File:** `tests/test_analytics_store_enforcement.py`

**Test Classes:**

1. **TestAnalyticsStoreMissingRoute** (4 tests)
   - ✅ SaaS mode missing route → HTTP 503
   - ✅ Enterprise mode missing route → HTTP 503
   - ✅ System mode missing route → HTTP 503
   - ✅ Lab mode missing route → warning + continue

2. **TestAnalyticsStoreIngest** (2 tests)
   - ✅ Ingest with attribution fields
   - ✅ Ingest missing route (lab mode) → RuntimeError

3. **TestAnalyticsStoreQuery** (2 tests)
   - ✅ Query with time range filters
   - ✅ Query with attribute filters

4. **TestAnalyticsStoreAggregate** (1 test)
   - ✅ Aggregate pageview metrics with grouping

5. **TestAnalyticsStoreHTTPRoutes** (5 tests)
   - ✅ POST /ingest success → 200
   - ✅ POST /ingest missing event_type → 400
   - ✅ POST /ingest missing route → 503
   - ✅ GET /query success → 200
   - ✅ DELETE /event/{id} success → 204

**Run Tests:**
```bash
cd /Users/jaynowman/dev/northstar-engines
pytest tests/test_analytics_store_enforcement.py -v
```

---

## Verification Checklist

### ✅ Code Complete
- [x] `service_reject.py`: Routing enforcement + exception handling
- [x] `routes.py`: HTTP handlers with 503 on missing route
- [x] `test_analytics_store_enforcement.py`: 14 integration tests

### ✅ Failure Mode Validation
- [x] Missing route in SaaS mode → HTTP 503 (not 400/404)
- [x] Error message includes configuration instructions
- [x] Lab mode: warning logged, continues (debug tolerance)
- [x] All routes propagate 503 to client

### ✅ Attribution Field Compliance
- [x] UTM fields supported (source, medium, campaign, content, term)
- [x] SEO fields supported (slug, title, description)
- [x] Dimensional fields supported (app, surface, platform, session_id)
- [x] Request context linked (tenant_id, run_id, request_id, step_id)

### ✅ Integration Points
- [x] Routing registry integration (`routing_registry().get_route()`)
- [x] Backend adapter selection (Firestore/DynamoDB/Cosmos)
- [x] Request context propagation (identity enforcement from AUTH-01)
- [x] Exception propagation to HTTP layer

---

## Unblocked Features

✅ **Agents Analytics Durability:** Agents can now reliably track:
- Page impressions by surface
- CTA interactions by utm_campaign
- Form submissions by utm_source
- Bounce rates and session metrics

✅ **UI Analytics Durability:** UI components can now emit:
- Pageview events with surface attribution
- CTA click events with utm_* metadata
- Form submission events with payload

✅ **Attribution Pipeline:** Analytics data now includes:
- Organic vs. paid traffic separation
- Campaign-level performance tracking
- Surface/page-level engagement metrics
- Session-level funnel analysis

---

## Production Deployment Checklist

### Before Deploying:

1. **Routing Configuration**
   - [ ] Create routing entry: `resource_kind: analytics_store`
   - [ ] Specify backend_type (firestore|dynamodb|cosmos)
   - [ ] Configure credentials/connection strings
   - [ ] Test routing entry: `GET /routing/routes?resource_kind=analytics_store`

2. **Monitoring**
   - [ ] Alert on HTTP 503 from `/analytics/ingest` (route missing)
   - [ ] Monitor analytics event ingest rate
   - [ ] Track query latency (ensure backend responsiveness)

3. **Clients Update**
   - [ ] Agents: Call `/analytics/ingest` with `utm_source`, `utm_campaign`
   - [ ] UI: Call `/analytics/ingest` with `surface`, `app`, `platform`
   - [ ] Ensure payload field is always JSON-serializable

4. **Data Migration** (if needed)
   - [ ] Backup existing in-memory analytics (if any)
   - [ ] Migrate historical events to configured backend
   - [ ] Verify data consistency before cutover

### Deployment Command:
```bash
# Restart service (picks up routing config)
docker-compose restart northstar-engines

# Verify routes live
curl http://localhost:5000/routing/routes?resource_kind=analytics_store

# Test ingest (should succeed if route configured)
curl -X POST http://localhost:5000/analytics/ingest \
  -H "Content-Type: application/json" \
  -d '{"event_type": "pageview", "payload": {}, "utm_source": "test"}'
  
# Should return 200 (route found) or 503 (route missing)
```

---

## Related Items

| Item | Status | Purpose |
|------|--------|---------|
| **AUTH-01** | ✅ Complete | Identity/tenant routing (precondition) |
| **TL-01** | ✅ Complete | Telemetry store enforcement |
| **MEM-01** | ✅ Complete | Memory store enforcement |
| **BB-01** | ✅ Complete | Blackboard store enforcement |
| **Agents Feature** | 🟡 Blocked Until Deploy | Use `/analytics/ingest` for durability |
| **UI Feature** | 🟡 Blocked Until Deploy | Use `/analytics/ingest` for durability |

---

## Files Modified/Created

| File | Change | Status |
|------|--------|--------|
| `engines/analytics/service_reject.py` | Created | ✅ Complete |
| `engines/analytics/routes.py` | Created | ✅ Complete |
| `tests/test_analytics_store_enforcement.py` | Created | ✅ Complete |

---

## Next Steps

1. **Deploy AN-01** to dev/staging
2. **Configure routing entry** for your backend choice
3. **Run integration tests** in staging
4. **Update Agents** to emit `/analytics/ingest` calls
5. **Update UI** to emit `/analytics/ingest` calls
6. **Monitor** ingest rate and query latency
7. **Deploy to production** when confident

---

**Implementation Date:** 2025-01-02  
**Verification Status:** READY FOR DEPLOYMENT  
**Next Review:** Post-deployment feedback  
