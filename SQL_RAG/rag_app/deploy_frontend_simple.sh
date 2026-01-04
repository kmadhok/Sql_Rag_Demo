#!/bin/bash
# React Frontend Deployment (Simple - No Dockerfile)
# Uses Google Cloud Run Node.js buildpacks

set -e

echo "🚀 React Frontend - Simple Buildpack Deployment"
echo "================================================"
echo

# Configuration
PROJECT_ID="${PROJECT_ID:-brainrot-453319}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="sql-rag-frontend-simple"
MEMORY="${MEMORY:-512Mi}"
CPU="${CPU:-1}"

# Get backend URL (optional - can be set manually)
BACKEND_URL="${BACKEND_URL:-}"

# If backend URL not provided, try to get it from existing service
if [ -z "$BACKEND_URL" ]; then
  echo "Attempting to get backend URL from sql-rag-api-simple service..."
  BACKEND_URL=$(gcloud run services describe sql-rag-api-simple \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --format='value(status.url)' 2>/dev/null || echo "")

  if [ -z "$BACKEND_URL" ]; then
    echo "Warning: Could not auto-detect backend URL."
    echo "Frontend will use default API endpoint."
    echo "You can set BACKEND_URL environment variable to override."
  else
    echo "Using backend URL: $BACKEND_URL"
  fi
fi

echo ""
echo "Deploying React frontend to Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo ""

# Navigate to frontend directory
cd frontend

# Deploy using buildpacks from frontend directory
echo "🔨 Building and deploying with Node.js buildpacks..."
echo ""

if [ -n "$BACKEND_URL" ]; then
  # Deploy with backend URL
  gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --memory "$MEMORY" \
    --cpu "$CPU" \
    --max-instances 5 \
    --timeout 60 \
    --set-env-vars "VITE_API_BASE_URL=$BACKEND_URL"
else
  # Deploy without backend URL (will use default)
  gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --memory "$MEMORY" \
    --cpu "$CPU" \
    --max-instances 5 \
    --timeout 60
fi

# Return to parent directory
cd ..

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Service URL:"
FRONTEND_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')
echo "$FRONTEND_URL"
echo ""

# Optionally update backend CORS if backend URL was detected
if [ -n "$BACKEND_URL" ]; then
  echo "💡 To update backend CORS configuration, run:"
  echo "   gcloud run services update sql-rag-api-simple \\"
  echo "     --region $REGION \\"
  echo "     --update-env-vars \"CORS_ORIGINS=$FRONTEND_URL\""
  echo ""
fi
