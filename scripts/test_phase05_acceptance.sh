#!/bin/bash
set -e

# Phase 0.5 Lane 2 Acceptance Test
# Tests: filesystem adapters (lab-only) + backend-class guard
# Verifies: Routes created, backends work in lab, forbidden in saas

BASE_URL="http://localhost:8010"
TENANT_ID="t_demo"
ENV="dev"
PROJECT_ID="p_internal"

echo "========================================="
echo "Phase 0.5 Lane 2 Acceptance Test"
echo "BASE_URL: $BASE_URL"
echo "========================================="

# Helper: Create a route
create_route() {
    local resource_kind=$1
    local backend_type=$2
    
    echo ""
    echo ">>> Creating route: $resource_kind -> $backend_type"
    
    curl -X POST "$BASE_URL/routing/routes" \
        -H "Content-Type: application/json" \
        -H "X-Tenant-Id: $TENANT_ID" \
        -H "X-Mode: lab" \
        -d "{
            \"resource_kind\": \"$resource_kind\",
            \"tenant_id\": \"$TENANT_ID\",
            \"env\": \"$ENV\",
            \"project_id\": \"$PROJECT_ID\",
            \"backend_type\": \"$backend_type\",
            \"config\": {\"base_dir\": \"var/$resource_kind\"},
            \"required\": true
        }"
    
    echo ""
}

# Test 1: Create routes for all resource kinds (with lab mode)
echo ""
echo "========= TEST 1: Create Routes (lab mode) ========="
create_route "event_stream" "filesystem"
create_route "object_store" "filesystem"
create_route "tabular_store" "filesystem"
create_route "metrics_store" "filesystem"

# Test 2: Timeline (event_stream) - LAB MODE (should work)
echo ""
echo "========= TEST 2A: Timeline in LAB mode (should succeed) ========="
echo ""
echo ">>> Appending event to timeline"
EVENT_RESPONSE=$(curl -s -X POST "$BASE_URL/realtime/timeline/thread_test/append" \
    -H "Content-Type: application/json" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "X-Mode: lab" \
    -H "X-Env: $ENV" \
    -d '{
        "type": "message",
        "stream_id": "thread_test",
        "content": "Hello from test",
        "user_id": "user_123"
    }')
echo "$EVENT_RESPONSE" | jq .
EVENT_ID=$(echo "$EVENT_RESPONSE" | jq -r '.event_id // empty')

echo ""
echo ">>> Listing events after $EVENT_ID"
curl -s -X GET "$BASE_URL/realtime/timeline/thread_test/list?after_event_id=$EVENT_ID" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "X-Mode: lab" \
    -H "X-Env: $ENV" | jq .

# Test 2B: Timeline (event_stream) - SAAS MODE (should fail with forbidden_backend_class)
echo ""
echo "========= TEST 2B: Timeline in SAAS mode (should fail with FORBIDDEN_BACKEND_CLASS) ========="
echo ""
echo ">>> Attempting to append event in SAAS mode (expect 403 error)"
SAAS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/realtime/timeline/thread_test/append" \
    -H "Content-Type: application/json" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "X-Mode: saas" \
    -H "X-Env: $ENV" \
    -d '{
        "type": "message",
        "stream_id": "thread_test",
        "content": "Should fail",
        "user_id": "user_123"
    }')
echo "$SAAS_RESPONSE" | head -1 | jq . 2>/dev/null || echo "$SAAS_RESPONSE" | head -1
HTTP_CODE=$(echo "$SAAS_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
echo "HTTP Status: $HTTP_CODE (expect 403)"
if [[ "$HTTP_CODE" == "403" ]]; then
    echo "✓ Correctly rejected with forbidden_backend_class"
else
    echo "✗ FAILED: Expected 403, got $HTTP_CODE"
fi

# Test 3A: Object Store - LAB MODE (should work)
echo ""
echo "========= TEST 3A: Object Store in LAB mode (should succeed) ========="
echo ""
echo ">>> Putting blob to object store"
PUT_RESPONSE=$(curl -s -X POST "$BASE_URL/nexus/raw/put" \
    -H "Content-Type: application/octet-stream" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "X-Mode: lab" \
    -H "X-Key: test_artifact.txt" \
    -d "Sample artifact content")
echo "$PUT_RESPONSE" | jq . 2>/dev/null || echo "$PUT_RESPONSE"

echo ""
echo ">>> Getting blob from object store"
curl -s -X GET "$BASE_URL/nexus/raw/get?key=test_artifact.txt" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "X-Mode: lab"
echo ""

# Test 3B: Object Store - SAAS MODE (should fail)
echo ""
echo "========= TEST 3B: Object Store in SAAS mode (should fail with FORBIDDEN_BACKEND_CLASS) ========="
echo ""
echo ">>> Attempting to put blob in SAAS mode (expect 403 error)"
SAAS_PUT=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/nexus/raw/put" \
    -H "Content-Type: application/octet-stream" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "X-Mode: saas" \
    -H "X-Key: test_artifact_saas.txt" \
    -d "Should fail")
echo "$SAAS_PUT" | head -1 | jq . 2>/dev/null || echo "$SAAS_PUT" | head -1
HTTP_CODE=$(echo "$SAAS_PUT" | grep "HTTP_CODE" | cut -d: -f2)
echo "HTTP Status: $HTTP_CODE (expect 403)"
if [[ "$HTTP_CODE" == "403" ]]; then
    echo "✓ Correctly rejected with forbidden_backend_class"
else
    echo "✗ FAILED: Expected 403, got $HTTP_CODE"
fi

# Test 4: Verify filesystem persistence
echo ""
echo "========= TEST 4: Filesystem Persistence Verification ========="

echo ""
echo ">>> Checking var/object_store"
find var/object_store -type f 2>/dev/null || echo "No object_store files yet"

echo ""
echo ">>> Checking var/tabular_store"
find var/tabular_store -type f 2>/dev/null || echo "No tabular_store files yet"

echo ""
echo ">>> Checking var/metrics_store"
find var/metrics_store -type f 2>/dev/null || echo "No metrics_store files yet"

echo ""
echo "========================================="
echo "Acceptance tests complete!"
echo "========================================="
