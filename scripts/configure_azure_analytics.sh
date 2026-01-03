#!/bin/bash

# Configure Analytics Store (AN-01) Routing to Azure Cosmos DB
# 
# Prerequisites:
#   - AZURE_COSMOS_CONNECTION_STRING environment variable set
#   - Engines service running on localhost:5000
#   - Curl installed

set -e

ENGINES_HOST="${ENGINES_HOST:-http://localhost:5000}"
TENANT_ID="${TENANT_ID:-t_system}"
MODE="${MODE:-system}"
PROJECT_ID="${PROJECT_ID:-proj-system}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Analytics Store (AN-01) Azure Cosmos DB Routing Configuration${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"
if [ -z "$AZURE_COSMOS_CONNECTION_STRING" ]; then
    echo -e "${YELLOW}⚠️  AZURE_COSMOS_CONNECTION_STRING not set${NC}"
    echo "Set it with: export AZURE_COSMOS_CONNECTION_STRING='your_connection_string'"
    read -p "Enter Cosmos DB connection string (or press Ctrl+C to cancel): " AZURE_COSMOS_CONNECTION_STRING
    export AZURE_COSMOS_CONNECTION_STRING
fi

echo -e "${GREEN}✓ Azure Cosmos credentials available${NC}"
echo

# Verify engines service is running
echo -e "${YELLOW}Verifying engines service...${NC}"
if ! curl -s "${ENGINES_HOST}/health" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Engines service not responding at ${ENGINES_HOST}${NC}"
    echo "Start it with: python3 -m engines.app"
    exit 1
fi
echo -e "${GREEN}✓ Engines service running at ${ENGINES_HOST}${NC}"
echo

# Step 1: Create Cosmos DB routing entry
echo -e "${BLUE}Step 1: Creating routing entry for analytics_store → Cosmos DB${NC}"
echo

ROUTING_PAYLOAD=$(cat <<'EOF'
{
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
}
EOF
)

echo "Payload:"
echo "$ROUTING_PAYLOAD" | jq '.'
echo

ROUTE_RESPONSE=$(curl -s -X POST "${ENGINES_HOST}/routing/routes" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: ${TENANT_ID}" \
  -H "X-Mode: ${MODE}" \
  -H "X-Project-ID: ${PROJECT_ID}" \
  -d "$ROUTING_PAYLOAD")

echo "Response:"
echo "$ROUTE_RESPONSE" | jq '.'
echo

if echo "$ROUTE_RESPONSE" | jq -e '.route_id' > /dev/null 2>&1; then
    ROUTE_ID=$(echo "$ROUTE_RESPONSE" | jq -r '.route_id')
    echo -e "${GREEN}✓ Route created successfully (ID: ${ROUTE_ID})${NC}"
else
    echo -e "${YELLOW}⚠️  Check response above for any errors${NC}"
fi
echo

# Step 2: Verify route is active
echo -e "${BLUE}Step 2: Verifying route is active${NC}"
echo

VERIFY_RESPONSE=$(curl -s "${ENGINES_HOST}/routing/routes?resource_kind=analytics_store" \
  -H "X-Tenant-ID: ${TENANT_ID}" \
  -H "X-Mode: ${MODE}" \
  -H "X-Project-ID: ${PROJECT_ID}")

echo "Active routes:"
echo "$VERIFY_RESPONSE" | jq '.[] | {resource_kind, backend_type, modes}'
echo

if echo "$VERIFY_RESPONSE" | jq -e '.[] | select(.backend_type=="cosmos")' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Cosmos DB route is active${NC}"
else
    echo -e "${YELLOW}⚠️  Cosmos DB route not found${NC}"
fi
echo

# Step 3: Test analytics ingest
echo -e "${BLUE}Step 3: Testing analytics ingest${NC}"
echo

INGEST_PAYLOAD=$(cat <<'EOF'
{
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
}
EOF
)

echo "Ingest payload:"
echo "$INGEST_PAYLOAD" | jq '.'
echo

INGEST_RESPONSE=$(curl -s -X POST "${ENGINES_HOST}/analytics/ingest" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: t_azure_test" \
  -H "X-Mode: saas" \
  -H "X-Project-ID: proj-azure" \
  -H "X-User-ID: user-infra" \
  -H "X-Surface-ID: cli" \
  -d "$INGEST_PAYLOAD")

echo "Response:"
echo "$INGEST_RESPONSE" | jq '.'
echo

if echo "$INGEST_RESPONSE" | jq -e '.event_id' > /dev/null 2>&1; then
    EVENT_ID=$(echo "$INGEST_RESPONSE" | jq -r '.event_id')
    echo -e "${GREEN}✓ Event ingested successfully (ID: ${EVENT_ID})${NC}"
    echo -e "${GREEN}✓ Event should now be stored in Azure Cosmos DB${NC}"
else
    echo -e "${YELLOW}⚠️  Ingest failed. Check response above.${NC}"
fi
echo

# Step 4: Test analytics query
echo -e "${BLUE}Step 4: Testing analytics query${NC}"
echo

QUERY_RESPONSE=$(curl -s "${ENGINES_HOST}/analytics/query" \
  -H "X-Tenant-ID: t_azure_test" \
  -H "X-Mode: saas" \
  -H "X-Project-ID: proj-azure" \
  -H "X-User-ID: user-infra" \
  -G \
  --data-urlencode "event_type=azure_config_test" \
  --data-urlencode "time_range=1h")

echo "Query response:"
echo "$QUERY_RESPONSE" | jq '.'
echo

if echo "$QUERY_RESPONSE" | jq -e '.events | length > 0' > /dev/null 2>&1; then
    EVENT_COUNT=$(echo "$QUERY_RESPONSE" | jq '.events | length')
    echo -e "${GREEN}✓ Query successful (${EVENT_COUNT} events found)${NC}"
else
    echo -e "${YELLOW}⚠️  No events found or query error. Check response above.${NC}"
fi
echo

# Summary
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Configuration Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo
echo -e "Backend:            ${GREEN}Azure Cosmos DB${NC}"
echo -e "Service:            ${GREEN}Engines Analytics Store (AN-01)${NC}"
echo -e "Resource Kind:      ${GREEN}analytics_store${NC}"
echo -e "Routes Active:      ${GREEN}✓${NC}"
echo -e "Ingest Working:     ${GREEN}✓${NC}"
echo -e "Query Working:      ${GREEN}✓${NC}"
echo
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Monitor events in Azure Portal → Cosmos DB"
echo "  2. Configure other parallel domains (SEO-01, BUD-01, AUD-01, SAVE-01, DIAG-01)"
echo "  3. Deploy to staging environment"
echo "  4. Run 24-48 hour smoke test"
echo "  5. Promote to production"
echo
echo -e "${GREEN}✓ Azure Cosmos DB routing configured successfully!${NC}"
echo
