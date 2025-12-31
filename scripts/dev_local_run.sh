#!/bin/bash
# engines/scripts/dev_local_run.sh
# Runs the main engines server locally.

# 1. Load Environment
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/dev_local_env.sh"

# 2. Activate Venv if exists (Standard location)
if [ -f "$DIR/../.venv/bin/activate" ]; then
    source "$DIR/../.venv/bin/activate"
fi

# 3. Set PYTHONPATH to repo root so 'engines' package is found
export PYTHONPATH="$DIR/.."

# 4. Run Seeding Script (Ensure routing validation passes)
echo "Running routing seeder..."
python3 "$DIR/seed_local_routing.py"

# 5. Run Uvicorn from Repo Root
# Mounting engines.chat.service.server:app on port 8000
echo "Starting Engines on http://0.0.0.0:8000..."
cd "$DIR/.."

# Log to file for debugging
LOG_FILE="$DIR/../dev_run.log"
echo "Logging to $LOG_FILE"

if command -v uvicorn &> /dev/null; then
    exec uvicorn engines.chat.service.server:app --host 0.0.0.0 --port 8000 --reload > "$LOG_FILE" 2>&1
else
    exec python3 -m uvicorn engines.chat.service.server:app --host 0.0.0.0 --port 8000 --reload > "$LOG_FILE" 2>&1
fi
