#!/usr/bin/env bash
set -euo pipefail

# Make sure Streamlit doesn't try to open a browser
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
export STREAMLIT_SERVER_HEADLESS=true

MODE="${INIT_MODE:-serve}"
if [[ "$MODE" == "precompute" ]]; then
  echo "Running precompute pipeline..."
  /bin/bash /app/scripts/precompute.sh
  echo "Precompute finished. Container exiting as requested."
  exit 0
fi

# Default: serve the app
echo "Starting Streamlit app..."
exec streamlit run /app/app_simple_gemini.py --server.port=${STREAMLIT_SERVER_PORT:-8502} --server.address=0.0.0.0

