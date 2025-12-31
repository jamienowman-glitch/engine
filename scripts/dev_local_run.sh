#!/usr/bin/env bash
# Start Firestore emulator, seed required control-plane data, and run the FastAPI app.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="${HOME}/google-cloud-sdk/bin:${PATH}"
if [[ -d "/opt/homebrew/opt/openjdk@21/bin" ]]; then
  export PATH="/opt/homebrew/opt/openjdk@21/bin:${PATH}"
fi

if [[ ! -f "${ROOT_DIR}/scripts/dev_local_env.sh" ]]; then
  echo "Missing scripts/dev_local_env.sh; aborting" >&2
  exit 1
fi
source "${ROOT_DIR}/scripts/dev_local_env.sh"
export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}"

mkdir -p "${HOME}/.northstar/"{logs,budget,audit,raw,datasets}

PORT=${PORT:-8010}
FS_PORT=8900
FS_LOG="${HOME}/.northstar/firestore.log"
FS_PID_FILE="${HOME}/.northstar/firestore.pid"

ensure_java() {
  if ! command -v java >/dev/null 2>&1; then
    echo "Java runtime not found. Install a JDK (e.g., brew install --cask temurin@21 or brew install openjdk@21) before running." >&2
    exit 1
  fi
}

start_firestore_emulator() {
  if nc -z localhost "${FS_PORT}" >/dev/null 2>&1; then
    echo "Firestore emulator already running on localhost:${FS_PORT}"
    return
  fi

  ensure_java
  if ! command -v gcloud >/dev/null 2>&1; then
    echo "gcloud CLI is required to start the Firestore emulator. Install Google Cloud SDK first." >&2
    exit 1
  fi

  echo "Starting Firestore emulator on localhost:${FS_PORT} ..."
  gcloud components install cloud-firestore-emulator -q >/dev/null 2>&1 || true
  gcloud beta emulators firestore start \
    --project "${GCP_PROJECT}" \
    --host-port="localhost:${FS_PORT}" \
    --quiet \
    >"${FS_LOG}" 2>&1 &
  local fs_pid=$!
  echo "${fs_pid}" > "${FS_PID_FILE}"

  for _ in {1..10}; do
    if nc -z localhost "${FS_PORT}" >/dev/null 2>&1; then
      echo "Firestore emulator is listening on localhost:${FS_PORT}"
      return
    fi

    if ! kill -0 "${fs_pid}" >/dev/null 2>&1; then
      echo "Firestore emulator process exited early. Check ${FS_LOG} for details." >&2
      exit 1
    fi

    sleep 1
  done

  kill "${fs_pid}" >/dev/null 2>&1 || true
  echo "Firestore emulator failed to start on localhost:${FS_PORT}. Check ${FS_LOG} for details." >&2
  exit 1
}

seed_control_plane() {
  python3 "${ROOT_DIR}/scripts/seed_dev_firestore.py"
}

start_firestore_emulator
seed_control_plane

echo "Starting uvicorn on :${PORT}"
python3 -m uvicorn engines.chat.service.server:app --host 0.0.0.0 --port "${PORT}" &
UVICORN_PID=$!

for _ in {1..10}; do
  if nc -z localhost "${PORT}" >/dev/null 2>&1; then
    status_code="$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}/ops/status" || true)"
    if [[ "${status_code}" == "200" ]]; then
      echo "Engines ready on http://localhost:${PORT} (/ops/status returned 200)"
      wait "${UVICORN_PID}"
      exit $?
    fi
  fi

  if ! kill -0 "${UVICORN_PID}" >/dev/null 2>&1; then
    echo "uvicorn process exited early; check console output for details." >&2
    exit 1
  fi

  sleep 1
done

echo "uvicorn failed health checks on http://localhost:${PORT}/ops/status; exiting." >&2
kill "${UVICORN_PID}" >/dev/null 2>&1 || true
exit 1
