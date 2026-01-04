#!/bin/bash
# Ultra-Simple Cloud Run Deployment (No Dockerfile Required)
# Cloud Run uses buildpacks to automatically build your container

set -e

# Load environment variables from .env.deploy if it exists
if [ -f .env.deploy ]; then
  echo "Loading environment from .env.deploy..."
  export $(grep -v '^#' .env.deploy | xargs)
else
  echo "Warning: .env.deploy not found. Using environment variables from shell."
fi

# Configuration
PROJECT_ID="${PROJECT_ID:-brainrot-453319}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-sql-rag-api-simple}"
MEMORY="${MEMORY:-2Gi}"
CPU="${CPU:-2}"

# Check required variables
if [ -z "$OPENAI_API_KEY" ] || [ -z "$GEMINI_API_KEY" ]; then
  echo "Error: OPENAI_API_KEY and GEMINI_API_KEY must be set"
  echo "Either set them in .env.deploy or export them in your shell"
  exit 1
fi

echo "Deploying $SERVICE_NAME to Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Deploy using source code (no Dockerfile needed!)
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory "$MEMORY" \
  --cpu "$CPU" \
  --max-instances 10 \
  --timeout 300 \
  --set-env-vars "PYTHONUNBUFFERED=1,EMBEDDINGS_PROVIDER=openai,BIGQUERY_PROJECT_ID=$PROJECT_ID,BIGQUERY_DATASET=bigquery-public-data.thelook_ecommerce,CORS_ORIGINS=*,OPENAI_API_KEY=$OPENAI_API_KEY,GEMINI_API_KEY=$GEMINI_API_KEY"

echo ""
echo "Deployment complete!"
echo ""
echo "Service URL:"
gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)'
echo ""
echo "API Docs:"
echo "$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')/docs"
