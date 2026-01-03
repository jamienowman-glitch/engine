#!/bin/bash

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "AN-01: Analytics Store Deployment to Staging"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# =========== Step 1: Verify Tests Pass ===========
echo "Step 1/4: Running analytics store enforcement tests..."
cd /Users/jaynowman/dev/northstar-engines

pytest tests/test_analytics_store_enforcement.py -v --tb=short
if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Fix errors before deploying."
    exit 1
fi
echo "✅ All tests passed"
echo ""

# =========== Step 2: Verify Syntax ===========
echo "Step 2/4: Verifying Python syntax..."
python3 -m py_compile \
    engines/analytics/service_reject.py \
    engines/analytics/routes.py \
    engines/routing/resource_kinds.py
echo "✅ Syntax check passed"
echo ""

# =========== Step 3: Display Routing Configuration ===========
echo "Step 3/4: Routing Configuration for analytics_store"
echo "────────────────────────────────────────────────────"
echo ""
echo "Configure ONE of the following routes via HTTP POST /routing/routes:"
echo ""
echo "Option A: Firestore Backend (GCP)"
cat << 'EOF'
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
EOF
echo ""

echo "Option B: DynamoDB Backend (AWS)"
cat << 'EOF'
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
EOF
echo ""

echo "Option C: Cosmos Backend (Azure)"
cat << 'EOF'
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
EOF
echo ""

echo "Example curl command to configure:"
echo "────────────────────────────────────"
echo ""
echo 'curl -X POST http://localhost:5000/routing/routes \'
echo '  -H "Content-Type: application/json" \'
echo '  -H "X-Tenant-ID: t_system" \'
echo '  -H "X-Mode: system" \'
echo '  -H "X-Project-ID: proj-system" \'
echo '  -d @analytics_store_route.json'
echo ""

# =========== Step 4: Display Next Steps ===========
echo "Step 4/4: Deployment Checklist"
echo "──────────────────────────────"
echo ""
echo "Before deploying to staging:"
echo ""
echo "  1. Choose backend (Firestore/DynamoDB/Cosmos)"
echo "  2. Create routing entry via POST /routing/routes"
echo "  3. Verify route: GET /routing/routes?resource_kind=analytics_store"
echo "  4. Restart engines service: docker-compose restart northstar-engines"
echo "  5. Run smoke test (see below)"
echo ""
echo "Smoke Test (after restart):"
echo "───────────────────────────"
echo ""
echo "curl -X POST http://localhost:5000/analytics/ingest \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'X-Tenant-ID: t_system' \\"
echo "  -H 'X-Mode: system' \\"
echo "  -H 'X-Project-ID: proj-system' \\"
echo "  -d '{
    \"event_type\": \"test_event\",
    \"payload\": {\"test\": true},
    \"utm_source\": \"test\",
    \"app\": \"staging_test\"
  }'"
echo ""
echo "Expected response:"
echo "  200 OK with event_id (route configured)"
echo "  503 analytics_store.missing_route (route not configured)"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "✅ AN-01 Deployment Package Ready"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Summary:"
echo "  ✅ Analytics store enforcement tests passing"
echo "  ✅ Python syntax verified"
echo "  ✅ Three backend options (Firestore/DynamoDB/Cosmos)"
echo "  ✅ Routing configuration ready"
echo ""
echo "Next: Configure routing entry and restart services"
echo ""
