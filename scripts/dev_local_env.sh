#!/bin/bash
# engines/scripts/dev_local_env.sh
# Sets up local filesystem-backed environment for Northstar Engines.

# 3. Create core local directories
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$REPO_ROOT/.northstar/data"
mkdir -p "$REPO_ROOT/.northstar/logs"
mkdir -p "$REPO_ROOT/.northstar/uploads"
mkdir -p "$REPO_ROOT/.northstar/data/routing_registry"

# 1. Export core env vars
export ENVIRONMENT=local
export FILESYSTEM_BACKEND=true
export KNOWLEDGE_BACKEND=filesystem
export MEMORY_BACKEND=local
export BUDGET_BACKEND=filesystem
export USAGE_BACKEND=filesystem
export ROUTING_REGISTRY_BACKEND=filesystem
export ROUTING_REGISTRY_FS_DIR="$REPO_ROOT/.northstar/data/routing_registry"
export IDENTITY_BACKEND=memory  # Patched to allow local dev
# Default to mock/vertex if needed, can be overridden
export MODEL_PROVIDER=vertex
export GCP_PROJECT_ID=local-dev-project
export GCP_REGION=us-central1

# 2. Set Secrets
if [ -z "$ENGINES_TICKET_SECRET" ]; then
    export ENGINES_TICKET_SECRET="dev-local-ticket-secret-0000"
    echo "Set default ENGINES_TICKET_SECRET."
fi
if [ -z "$AUTH_JWT_SIGNING" ]; then
    export AUTH_JWT_SIGNING="dev-jwt-secret-1234"
    echo "Set default AUTH_JWT_SIGNING."
fi

echo "Environment Configured:"
echo "  REPO_ROOT: $REPO_ROOT"
echo "  ENVIRONMENT: $ENVIRONMENT"
echo "  FILESYSTEM_BACKEND: $FILESYSTEM_BACKEND"
echo "  KNOWLEDGE_BACKEND: $KNOWLEDGE_BACKEND"
echo "  BUDGET_BACKEND: $BUDGET_BACKEND"
echo "  ROUTING_REGISTRY_BACKEND: $ROUTING_REGISTRY_BACKEND"
echo "  IDENTITY_BACKEND: $IDENTITY_BACKEND"
echo "  ENGINES_TICKET_SECRET is set"
echo "  AUTH_JWT_SIGNING is set"
