#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=/app:${PYTHONPATH:-}

# Ensure Ollama is reachable
/bin/bash /app/scripts/wait-for-ollama.sh

EMBED_CSV_PATH="${EMBED_CSV:-data_new/sample_queries_with_metadata_recovered.csv}"
SCHEMA_CSV_PATH="${SCHEMA_CSV:-data_new/thelook_ecommerce_schema.csv}"
LOOKML_DIR_PATH="${LOOKML_DIR:-lookml_data}"
OUTPUT_DIR="${OUTPUT_DIR:-faiss_indices}"

echo "==> Generating embeddings from $EMBED_CSV_PATH"
python /app/standalone_embedding_generator.py \
  --csv "$EMBED_CSV_PATH" \
  --schema "$SCHEMA_CSV_PATH" \
  --lookml-dir "$LOOKML_DIR_PATH" \
  --output "$OUTPUT_DIR" \
  --incremental

ANALYTICS_CSV_PATH="${ANALYTICS_CSV:-sample_queries_with_metadata.csv}"
echo "==> Generating catalog analytics from $ANALYTICS_CSV_PATH"
python /app/catalog_analytics_generator.py --csv "$ANALYTICS_CSV_PATH"

echo "Precompute completed."

