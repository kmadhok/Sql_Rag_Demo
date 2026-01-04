#!/bin/bash
# React Frontend Deployment (Docker-based)
# Uses Dockerfile with build-time env vars for Vite compilation
# Run this script from the frontend/ directory

set -e

echo "🚀 React Frontend - Docker Deployment"
echo "======================================"
echo

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
FRONTEND_SERVICE="sql-rag-frontend-simple"
BACKEND_SERVICE="sql-rag-api-simple"
MEMORY="${MEMORY:-512Mi}"
CPU="${CPU:-1}"

echo "Deploying React frontend to Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Frontend Service: $FRONTEND_SERVICE"
echo "Backend Service: $BACKEND_SERVICE"
echo ""

# === OPERATIONAL PREREQUISITES ===
echo "🔧 Checking operational prerequisites..."
echo ""

# Check Artifact Registry repository exists
echo "1️⃣  Checking Artifact Registry..."
if ! gcloud artifacts repositories describe sql-rag-repo \
  --location="$REGION" \
  --project="$PROJECT_ID" &>/dev/null; then
  echo "⚠️  Repository 'sql-rag-repo' not found - creating..."
  gcloud artifacts repositories create sql-rag-repo \
    --repository-format=docker \
    --location="$REGION" \
    --description="SQL RAG application images" \
    --project="$PROJECT_ID"
  echo "✅ Repository created"
else
  echo "✅ Repository exists"
fi

# Check Cloud Build API enabled
echo "2️⃣  Checking Cloud Build API..."
if ! gcloud services list --enabled \
  --filter="name:cloudbuild.googleapis.com" \
  --project="$PROJECT_ID" 2>/dev/null | grep -q cloudbuild; then
  echo "⚠️  Cloud Build API not enabled - enabling..."
  gcloud services enable cloudbuild.googleapis.com --project="$PROJECT_ID"
  echo "✅ API enabled (may take a few minutes to propagate)"
  sleep 5  # Brief pause for API propagation
else
  echo "✅ API enabled"
fi

# Configure Docker authentication
echo "3️⃣  Configuring Docker authentication..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
echo "✅ Docker authentication configured"

echo ""

# Get backend URL
echo "🔍 Fetching backend URL..."
BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --format='value(status.url)' 2>/dev/null)

if [ -z "$BACKEND_URL" ]; then
  echo "❌ ERROR: Backend service '$BACKEND_SERVICE' not found!"
  echo "   Deploy the backend first using: ./deploy_api_simple.sh"
  exit 1
fi

echo "✅ Backend URL: $BACKEND_URL"
echo ""

# === BACKEND HEALTH VALIDATION ===
echo "🔍 Pre-flight checks: Backend validation"
echo "=========================================="
echo

# Test backend health endpoint
echo "4️⃣  Testing backend health endpoint..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -m 30 "$BACKEND_URL/health" 2>/dev/null)
[ -z "$HEALTH_STATUS" ] && HEALTH_STATUS="000"

if [ "$HEALTH_STATUS" != "200" ]; then
  echo "❌ FAILED: Backend health check failed (HTTP $HEALTH_STATUS)"
  echo "   URL: $BACKEND_URL/health"
  echo ""

  if [ "$HEALTH_STATUS" = "000" ]; then
    echo "   Could not connect to backend (timeout or connection refused)"
  fi

  echo "   Fix backend issues before deploying frontend"
  echo "   Check backend logs: gcloud run services logs read $BACKEND_SERVICE --region $REGION"
  exit 1
fi

echo "✅ Backend health check passed (HTTP 200)"
echo ""

# Test backend with sample query
echo "5️⃣  Testing backend with sample query..."
QUERY_RESPONSE=$(curl -s -X POST "$BACKEND_URL/query/search" \
  -H "Content-Type: application/json" \
  -d '{"question":"test query","top_k":1}' \
  -m 30 \
  2>/dev/null)
[ -z "$QUERY_RESPONSE" ] && QUERY_RESPONSE="FAILED"

# Check if response contains expected fields
QUERY_OK=true
if [[ "$QUERY_RESPONSE" == *"FAILED"* ]]; then
  echo "⚠️  WARNING: Could not connect to backend query endpoint"
  QUERY_OK=false
elif [[ "$QUERY_RESPONSE" != *"sql"* ]] && [[ "$QUERY_RESPONSE" != *"error"* ]]; then
  echo "⚠️  WARNING: Backend returned unexpected response format"
  echo "   Response: ${QUERY_RESPONSE:0:200}..."
  QUERY_OK=false
elif [[ "$QUERY_RESPONSE" == *"error"* ]]; then
  echo "⚠️  WARNING: Backend returned error response"
  echo "   This might indicate:"
  echo "   - FAISS embedding dimension mismatch (check EMBEDDINGS_PROVIDER)"
  echo "   - Vector store not initialized"
  echo "   - Database connection issues"
  echo ""
  echo "   Response: ${QUERY_RESPONSE:0:500}..."
  QUERY_OK=false
else
  echo "✅ Backend query test passed"
fi

# If query failed, ask user to confirm
if [ "$QUERY_OK" = false ]; then
  echo ""
  echo "⚠️  Backend may have issues. Deploy anyway?"
  echo ""
  read -p "Continue with deployment? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check backend logs: gcloud run services logs read $BACKEND_SERVICE --region $REGION"
    echo "2. Verify EMBEDDINGS_PROVIDER matches vector store"
    echo "3. Test backend directly: curl $BACKEND_URL/health"
    exit 1
  fi
fi

echo ""
echo "=========================================="
echo "✅ All pre-flight checks passed"
echo "=========================================="
echo ""

# Build Docker image with backend URL
echo "🔨 Building Docker image..."
echo "   Build arg: VITE_API_BASE_URL=$BACKEND_URL"
echo ""

IMAGE_NAME="us-central1-docker.pkg.dev/$PROJECT_ID/sql-rag-repo/sql-rag-frontend"
IMAGE_TAG="$IMAGE_NAME:latest"

# Verify Dockerfile exists
if [ ! -f Dockerfile ]; then
  echo "❌ ERROR: Dockerfile not found in current directory!"
  echo "   Run this script from the frontend/ directory"
  exit 1
fi

docker build . \
  --tag "$IMAGE_TAG" \
  --build-arg VITE_API_BASE_URL="$BACKEND_URL" \
  --platform linux/amd64

echo ""
echo "✅ Docker image built successfully"
echo ""

# Push to Artifact Registry
echo "📤 Pushing image to Artifact Registry..."
docker push "$IMAGE_TAG"

echo ""
echo "✅ Image pushed successfully"
echo ""

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy "$FRONTEND_SERVICE" \
  --image "$IMAGE_TAG" \
  --clear-base-image \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory "$MEMORY" \
  --cpu "$CPU" \
  --max-instances 10 \
  --timeout 300

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Frontend URL:"
gcloud run services describe "$FRONTEND_SERVICE" --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)'
echo ""
echo "Backend URL:"
echo "$BACKEND_URL"
