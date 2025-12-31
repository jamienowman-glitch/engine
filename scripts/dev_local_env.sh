#!/usr/bin/env bash
# Environment for running engines locally against Firestore emulator (no runtime code changes).

# Core env
export ENV=dev
export APP_ENV=dev
export GCP_PROJECT=northstar-dev
export GCP_PROJECT_ID="${GCP_PROJECT}"
export GOOGLE_CLOUD_PROJECT="${GCP_PROJECT}"

# Firestore-only backends (routing/identity/timeline/feature flags/realtime registry)
export FIRESTORE_EMULATOR_HOST=localhost:8900
export IDENTITY_BACKEND=firestore
export ROUTING_REGISTRY_BACKEND=firestore
export STREAM_TIMELINE_BACKEND=firestore
export FEATURE_FLAGS_BACKEND=firestore
export REALTIME_REGISTRY_BACKEND=firestore

# Durable filesystem backends
export BUDGET_BACKEND=filesystem
export BUDGET_BACKEND_FS_DIR="${HOME}/.northstar/budget"
export AUDIT_BACKEND=filesystem
export AUDIT_DIR="${HOME}/.northstar/audit"
export RAW_BUCKET="file://${HOME}/.northstar/raw"
export DATASETS_BUCKET="file://${HOME}/.northstar/datasets"
export KNOWLEDGE_BACKEND=filesystem

# Chat/realtime
export CHAT_BUS_BACKEND=redis
export REDIS_HOST=localhost
export REDIS_PORT=6379

# Auth/tickets
export AUTH_JWT_SIGNING=dev-local-signing-key
export ENGINES_TICKET_SECRET=dev-local-ticket

# Misc
export PYTHONUNBUFFERED=1
