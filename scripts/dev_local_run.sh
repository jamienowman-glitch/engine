#!/usr/bin/env bash
# Start Firestore emulator, seed required control-plane data, and run the FastAPI app.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="${HOME}/google-cloud-sdk/bin:${PATH}"

if [[ ! -f "${ROOT_DIR}/scripts/dev_local_env.sh" ]]; then
  echo "Missing scripts/dev_local_env.sh; aborting" >&2
  exit 1
fi
source "${ROOT_DIR}/scripts/dev_local_env.sh"

mkdir -p "${HOME}/.northstar/"{logs,budget,audit,raw,datasets}

PORT=${PORT:-8000}
FS_LOG="${HOME}/.northstar/firestore.log"
FS_PID_FILE="${HOME}/.northstar/firestore.pid"

start_firestore_emulator() {
  if nc -z localhost 8900 >/dev/null 2>&1; then
    echo "Firestore emulator already running on localhost:8900"
    return
  fi

  echo "Starting Firestore emulator on localhost:8900 ..."
  gcloud components install cloud-firestore-emulator -q >/dev/null 2>&1 || true
  gcloud beta emulators firestore start \
    --project "${GCP_PROJECT}" \
    --host-port=localhost:8900 \
    --quiet \
    --no-store-on-disk \
    >"${FS_LOG}" 2>&1 &
  echo $! > "${FS_PID_FILE}"
  sleep 5
}

seed_control_plane() {
  python3 "${ROOT_DIR}/scripts/seed_dev_firestore.py"
}

start_firestore_emulator
seed_control_plane

echo "Starting uvicorn on :${PORT}"
exec uvicorn engines.chat.service.server:app --host 0.0.0.0 --port "${PORT}"
