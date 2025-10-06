#!/usr/bin/env bash
set -euo pipefail

HOST="${OLLAMA_BASE_URL:-http://ollama:11434}"
URL="$HOST/api/tags"

echo "Waiting for Ollama at $URL ..."
for i in {1..60}; do
  if curl -sf "$URL" >/dev/null; then
    echo "Ollama is up."
    exit 0
  fi
  sleep 2
done

echo "Timed out waiting for Ollama at $URL"
exit 1

