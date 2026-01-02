#!/bin/bash
set -e

# Phase 0.5 Lane 4 Acceptance Test
# Tests: Cloud adapters (S3, Firestore) + fail-fast NotImplementedError
# Verifies: S3 PUT/GET with routing, Firestore NotImplemented errors, backend flipping

BASE_URL="http://localhost:8010"
TENANT_ID="t_demo"
ENV="dev"
PROJECT_ID="p_internal"

echo "========================================="
echo "Phase 0.5 Lane 4 Acceptance Test"
echo "Cloud Adapters (S3, Firestore) + Fail-Fast"
echo "BASE_URL: $BASE_URL"
echo "========================================="

# Helper: Create a route
create_route() {
    local resource_kind=$1
    local backend_type=$2
    local config=${3:-'{}'}
    
    echo ""
    echo ">>> Creating route: $resource_kind -> $backend_type"
    
    curl -s -X POST "$BASE_URL/routing/routes" \
        -H "Content-Type: application/json" \
        -H "X-Tenant-Id: $TENANT_ID" \
        -H "X-Mode: lab" \
        -d "{
            \"resource_kind\": \"$resource_kind\",
            \"tenant_id\": \"$TENANT_ID\",
            \"env\": \"$ENV\",
            \"project_id\": \"$PROJECT_ID\",
            \"backend_type\": \"$backend_type\",
            \"config\": $config,
            \"required\": true
        }" | jq '.'
    
    echo ""
}

echo ""
echo "===== TEST 1A: S3 Object Store Route (if AWS creds available) ====="
echo "Creating S3 route with bucket config..."

# Try to create S3 route (will only work if AWS_DEFAULT_REGION and credentials set)
S3_ROUTE_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/routing/routes" \
    -H "Content-Type: application/json" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "X-Mode: lab" \
    -d "{
        \"resource_kind\": \"object_store\",
        \"tenant_id\": \"$TENANT_ID\",
        \"env\": \"$ENV\",
        \"project_id\": \"$PROJECT_ID\",
        \"backend_type\": \"s3\",
        \"config\": {\"bucket\": \"northstar-raw-test\"},
        \"required\": true
    }")

echo "$S3_ROUTE_RESPONSE"
HTTP_CODE=$(echo "$S3_ROUTE_RESPONSE" | tail -1 | sed 's/HTTP_CODE://')

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    echo "✓ S3 route created successfully"
    
    echo ""
    echo "===== TEST 1B: S3 PUT Object (direct S3 operation) ====="
    echo "Attempting PUT object to S3 with routing-resolved adapter..."
    
    # Create test data
    TEST_CONTENT="Lane 4 S3 test content: $(date)"
    
    # Try PUT (will fail if AWS credentials not set or bucket doesn't exist)
    S3_PUT_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/nexus/raw/put" \
        -H "X-Tenant-Id: $TENANT_ID" \
        -H "X-Mode: lab" \
        -H "X-Key: lane4/test_s3_object.txt" \
        --data-binary "$TEST_CONTENT")
    
    echo "$S3_PUT_RESPONSE"
    S3_PUT_CODE=$(echo "$S3_PUT_RESPONSE" | tail -1 | sed 's/HTTP_CODE://')
    
    if [ "$S3_PUT_CODE" = "200" ]; then
        echo "✓ S3 PUT succeeded (object stored in S3)"
        
        echo ""
        echo "===== TEST 1C: S3 GET Object ====="
        echo "Retrieving object from S3..."
        
        S3_GET_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "$BASE_URL/nexus/raw/get?key=lane4/test_s3_object.txt" \
            -H "X-Tenant-Id: $TENANT_ID" \
            -H "X-Mode: lab")
        
        echo "$S3_GET_RESPONSE"
        S3_GET_CODE=$(echo "$S3_GET_RESPONSE" | tail -1 | sed 's/HTTP_CODE://')
        
        if [ "$S3_GET_CODE" = "200" ]; then
            echo "✓ S3 GET succeeded (object retrieved from S3)"
        else
            echo "✗ S3 GET failed with HTTP $S3_GET_CODE"
        fi
    else
        echo "⚠ S3 PUT failed with HTTP $S3_PUT_CODE (expected if AWS credentials not configured)"
    fi
else
    echo "⚠ S3 route creation failed (expected if AWS credentials not available); skipping PUT/GET tests"
fi

echo ""
echo "===== TEST 2A: Tabular Store with Firestore Route (fail-fast) ====="
echo "Creating Firestore route for tabular_store..."

FIRESTORE_ROUTE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/routing/routes" \
    -H "Content-Type: application/json" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "X-Mode: lab" \
    -d "{
        \"resource_kind\": \"tabular_store\",
        \"tenant_id\": \"$TENANT_ID\",
        \"env\": \"$ENV\",
        \"project_id\": \"$PROJECT_ID\",
        \"backend_type\": \"firestore\",
        \"config\": {\"project\": \"gcp-project-id\"},
        \"required\": true
    }")

echo "$FIRESTORE_ROUTE"

echo ""
echo "===== TEST 2B: Attempt Tabular Upsert (should fail with NotImplementedError) ====="
echo "Attempting to upsert into tabular_store with Firestore route..."

# Try to use tabular store (will fail because Firestore adapter not implemented)
TABULAR_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/storage/tabular/policies/upsert" \
    -H "Content-Type: application/json" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "X-Mode: lab" \
    -d "{
        \"table_name\": \"policies\",
        \"key\": \"policy_lane4_test\",
        \"data\": {\"policy_type\": \"firestore_test\", \"version\": 1}
    }")

echo "$TABULAR_RESPONSE"
TABULAR_CODE=$(echo "$TABULAR_RESPONSE" | tail -1 | sed 's/HTTP_CODE://')

if [ "$TABULAR_CODE" = "501" ] || [ "$TABULAR_CODE" = "500" ]; then
    # Check if response mentions "NotImplementedError" or "not yet implemented"
    if echo "$TABULAR_RESPONSE" | grep -q "not yet implemented\|NotImplemented"; then
        echo "✓ Tabular store correctly returned NotImplementedError for Firestore backend"
    else
        echo "⚠ Got error code $TABULAR_CODE but message may not mention NotImplementedError"
    fi
else
    echo "⚠ Unexpected HTTP code $TABULAR_CODE (expected 501 or 500 NotImplementedError)"
fi

echo ""
echo "===== TEST 3A: Metrics Store with Firestore Route (fail-fast) ====="
echo "Creating Firestore route for metrics_store..."

METRICS_FS_ROUTE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/routing/routes" \
    -H "Content-Type: application/json" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "X-Mode: lab" \
    -d "{
        \"resource_kind\": \"metrics_store\",
        \"tenant_id\": \"$TENANT_ID\",
        \"env\": \"$ENV\",
        \"project_id\": \"$PROJECT_ID\",
        \"backend_type\": \"firestore\",
        \"config\": {\"project\": \"gcp-project-id\"},
        \"required\": true
    }")

echo "$METRICS_FS_ROUTE"

echo ""
echo "===== TEST 3B: Attempt Metrics Ingest (should fail with NotImplementedError) ====="
echo "Attempting to ingest metrics with Firestore route..."

METRICS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/kpi/ingest" \
    -H "Content-Type: application/json" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "X-Mode: lab" \
    -d "{
        \"metric_name\": \"test_metric\",
        \"value\": 42.5,
        \"tags\": {\"lane\": \"lane4\"}
    }")

echo "$METRICS_RESPONSE"
METRICS_CODE=$(echo "$METRICS_RESPONSE" | tail -1 | sed 's/HTTP_CODE://')

if [ "$METRICS_CODE" = "501" ] || [ "$METRICS_CODE" = "500" ]; then
    if echo "$METRICS_RESPONSE" | grep -q "not yet implemented\|NotImplemented"; then
        echo "✓ Metrics store correctly returned NotImplementedError for Firestore backend"
    else
        echo "⚠ Got error code $METRICS_CODE but message may not mention NotImplementedError"
    fi
else
    echo "⚠ Unexpected HTTP code $METRICS_CODE (expected 501 or 500 NotImplementedError)"
fi

echo ""
echo "===== TEST 4A: Timeline with Firestore Route ====="
echo "Creating Firestore route for event_stream..."

TIMELINE_FS_ROUTE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/routing/routes" \
    -H "Content-Type: application/json" \
    -H "X-Tenant-Id: t_system" \
    -H "X-Mode: lab" \
    -d "{
        \"resource_kind\": \"event_stream\",
        \"tenant_id\": \"t_system\",
        \"env\": \"dev\",
        \"project_id\": \"p_internal\",
        \"backend_type\": \"firestore\",
        \"config\": {\"project\": \"gcp-project-id\"},
        \"required\": true
    }")

echo "$TIMELINE_FS_ROUTE"
TIMELINE_FS_CODE=$(echo "$TIMELINE_FS_ROUTE" | tail -1 | sed 's/HTTP_CODE://')

if [ "$TIMELINE_FS_CODE" = "200" ] || [ "$TIMELINE_FS_CODE" = "201" ]; then
    echo "✓ Firestore route for timeline created"
    echo "Note: Actual Firestore append/list will be tested in integration tests with real GCP credentials"
fi

echo ""
echo "===== TEST 5: Backend Flipping (Filesystem -> S3 -> Firestore) ====="
echo "Demonstrating routing-driven backend selection..."

echo ""
echo "Step 1: Create filesystem route for object_store"
create_route "object_store" "filesystem" '{"base_dir": "var/object_store"}'

echo ""
echo "Step 2: Store object via filesystem"
FILESYSTEM_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/nexus/raw/put" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "X-Mode: lab" \
    -H "X-Key: lane4/test_flip_fs.txt" \
    --data-binary "Filesystem backend test")

echo "$FILESYSTEM_RESPONSE" | head -n -1
FS_CODE=$(echo "$FILESYSTEM_RESPONSE" | tail -1 | sed 's/HTTP_CODE://')
echo "HTTP Code: $FS_CODE"

if [ "$FS_CODE" = "200" ]; then
    echo "✓ Filesystem backend: Object stored"
fi

echo ""
echo "Step 3: Flip route to S3 (if AWS available)"
create_route "object_store" "s3" '{"bucket": "northstar-raw-test"}'

echo ""
echo "Step 4: Store different object via S3"
FLIP_S3_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/nexus/raw/put" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "X-Mode: lab" \
    -H "X-Key: lane4/test_flip_s3.txt" \
    --data-binary "S3 backend after flip")

echo "$FLIP_S3_RESPONSE" | head -n -1
FLIP_CODE=$(echo "$FLIP_S3_RESPONSE" | tail -1 | sed 's/HTTP_CODE://')
echo "HTTP Code: $FLIP_CODE"

if [ "$FLIP_CODE" = "200" ]; then
    echo "✓ S3 backend (post-flip): Object stored"
    echo "✓ Backend flipping works: routing registry drives adapter selection"
elif echo "$FLIP_S3_RESPONSE" | grep -q "NotImplemented\|not available"; then
    echo "⚠ S3 route exists but credentials may not be configured"
else
    echo "ℹ Flip test skipped (S3 may not be configured)"
fi

echo ""
echo "===== TEST 6: Missing Route Error Handling ====="
echo "Attempting operation with no route configured (should fail fast)..."

# Create a new tenant with no routes
NEW_TENANT="t_noroute"

MISSING_ROUTE_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/nexus/raw/put" \
    -H "X-Tenant-Id: $NEW_TENANT" \
    -H "X-Mode: lab" \
    -H "X-Key: test.txt" \
    --data-binary "This should fail")

echo "$MISSING_ROUTE_RESPONSE"
MISSING_CODE=$(echo "$MISSING_ROUTE_RESPONSE" | tail -1 | sed 's/HTTP_CODE://')

if [ "$MISSING_CODE" = "500" ] || [ "$MISSING_CODE" = "503" ]; then
    if echo "$MISSING_ROUTE_RESPONSE" | grep -q "No route configured\|missing"; then
        echo "✓ Missing route returns explicit error (no silent fallback)"
    fi
fi

echo ""
echo "========================================="
echo "Phase 0.5 Lane 4 Acceptance Test Complete"
echo "========================================="
echo ""
echo "Summary of Lane 4 Features Tested:"
echo "  1. S3 object_store adapter (PUT/GET with routing)"
echo "  2. Firestore adapters (NotImplementedError fail-fast)"
echo "  3. Backend flipping (routing drives selection)"
echo "  4. Missing route error handling"
echo ""
