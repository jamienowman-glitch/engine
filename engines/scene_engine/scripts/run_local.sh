#!/usr/bin/env bash
set -euo pipefail
uvicorn engines.scene_engine.service.server:app --host 0.0.0.0 --port "${PORT:-8080}"
