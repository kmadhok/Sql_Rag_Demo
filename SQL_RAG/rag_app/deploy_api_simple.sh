#!/bin/bash
# FastAPI Backend Deployment (Simple - No Dockerfile)
# Uses Google Cloud Run buildpacks with forced entrypoint to bypass Streamlit detection

set -e

echo "🚀 FastAPI Backend - Simple Buildpack Deployment"
echo "=================================================="
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
SERVICE_NAME="sql-rag-api-simple"
MEMORY="${MEMORY:-2Gi}"
CPU="${CPU:-2}"

# Check required variables
if [ -z "$OPENAI_API_KEY" ] || [ -z "$GEMINI_API_KEY" ]; then
  echo "Error: OPENAI_API_KEY and GEMINI_API_KEY must be set"
  echo "Either set them in .env.deploy or export them in your shell"
  exit 1
fi

echo "Deploying FastAPI backend to Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo ""

# Verify requirements.txt exists (should be API-only version)
if [ ! -f requirements.txt ]; then
  echo "Error: requirements.txt not found!"
  echo "Ensure requirements.txt contains FastAPI dependencies (no Streamlit)"
  exit 1
fi

echo "📦 Using requirements.txt (API-only dependencies)"
echo ""

# === DEBUGGING: Requirements Analysis ===
echo ""
echo "🔍 DEBUG: Requirements File Analysis"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Working directory: $(pwd)"
echo "Requirements file: $(ls -lh requirements.txt | awk '{print $5, $6, $7, $8, $9}')"
echo ""
echo "📄 Full contents of requirements.txt:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat -n requirements.txt
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🔎 Searching for 'pyarrow' (direct reference):"
if grep -in "pyarrow" requirements.txt 2>/dev/null; then
  echo "   ⚠️  WARNING: Found 'pyarrow' in requirements.txt above!"
  echo "   Check if it's commented out properly (should start with #)"
else
  echo "   ✓ No direct pyarrow reference found"
fi
echo ""

echo "🔎 Checking for packages that depend on pyarrow (transitive dependencies):"
echo ""
echo "   Checking 'google-cloud-bigquery[pandas]' (pulls in pyarrow)..."
if grep -i "google-cloud-bigquery\[pandas\]" requirements.txt 2>/dev/null; then
  echo "   ⚠️  FOUND: google-cloud-bigquery[pandas] → This WILL install pyarrow!"
  echo "   FIX: Change to 'google-cloud-bigquery' (without [pandas])"
else
  echo "   ✓ Not using bigquery[pandas] extras"
fi
echo ""

echo "   Checking 'pandas' version (some versions recommend pyarrow)..."
if grep -i "^pandas" requirements.txt 2>/dev/null; then
  echo "   ℹ️  Found pandas - newer versions may optionally use pyarrow"
  echo "   (This is usually OK if pyarrow is not explicitly listed)"
else
  echo "   ✓ pandas not found"
fi
echo ""

echo "📦 All requirements*.txt files in this directory:"
ls -lh requirements*.txt 2>/dev/null | awk '{print "   ", $9, "-", $5}' || echo "   (none found)"
echo ""

echo "🚫 Checking .gcloudignore for exclusions:"
if [ -f .gcloudignore ]; then
  if grep -i "requirements" .gcloudignore 2>/dev/null; then
    echo "   ⚠️  Found 'requirements' in .gcloudignore - files might be excluded!"
  else
    echo "   ✓ requirements files not excluded in .gcloudignore"
  fi
else
  echo "   ✓ No .gcloudignore file (all files will be uploaded)"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "👀 Review the above output carefully."
echo "   If you see pyarrow or google-cloud-bigquery[pandas], that's the issue!"
echo ""
read -p "Press Enter to continue with deployment (or Ctrl+C to abort)..." || true
echo ""

# Hide Dockerfiles to force buildpack usage
echo "🔒 Temporarily hiding Dockerfiles to force buildpack detection..."
DOCKERFILES_HIDDEN=false
if [ -f Dockerfile.api ]; then
  mv Dockerfile.api Dockerfile.api.disabled
  echo "   Hidden: Dockerfile.api"
  DOCKERFILES_HIDDEN=true
fi
if [ -f Dockerfile ]; then
  mv Dockerfile Dockerfile.disabled
  echo "   Hidden: Dockerfile"
  DOCKERFILES_HIDDEN=true
fi

# Set up cleanup trap to restore Dockerfiles even if deployment fails
cleanup() {
  echo ""
  echo "🔄 Restoring Dockerfiles..."

  # Restore Dockerfiles
  if [ -f Dockerfile.api.disabled ]; then
    mv Dockerfile.api.disabled Dockerfile.api
    echo "   Restored: Dockerfile.api"
  fi
  if [ -f Dockerfile.disabled ]; then
    mv Dockerfile.disabled Dockerfile
    echo "   Restored: Dockerfile"
  fi
}

# Register cleanup function to run on exit (success or failure)
trap cleanup EXIT

# Deploy using buildpacks (no Dockerfiles present, so buildpacks will be used)
echo ""
echo "🔨 Building and deploying with buildpacks..."
echo "   ✓ Dockerfiles hidden (forcing buildpack detection)"
echo "   ✓ Using requirements.txt (API-only, no Streamlit)"
echo "   ✓ Buildpacks will auto-detect Python + FastAPI"
echo ""

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
  --set-env-vars "PYTHONUNBUFFERED=1,PYTHONPATH=/app,EMBEDDINGS_PROVIDER=gemini,BIGQUERY_PROJECT_ID=$PROJECT_ID,BIGQUERY_DATASET=bigquery-public-data.thelook_ecommerce,CORS_ORIGINS=*,OPENAI_API_KEY=$OPENAI_API_KEY,GEMINI_API_KEY=$GEMINI_API_KEY"

# Capture deployment result
DEPLOY_EXIT_CODE=$?

# === POST-DEPLOYMENT DEBUGGING (on failure) ===
if [ $DEPLOY_EXIT_CODE -ne 0 ]; then
  echo ""
  echo "❌ Deployment failed!"
  echo ""
  echo "🔍 Analyzing Cloud Build logs for pyarrow installation..."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  # Get the latest build ID for this region
  echo "Fetching latest Cloud Build..."
  LATEST_BUILD=$(gcloud builds list --region="$REGION" --limit=1 --format='value(id)' 2>/dev/null)

  if [ -n "$LATEST_BUILD" ]; then
    echo "Latest build ID: $LATEST_BUILD"
    echo ""

    # Search for pyarrow in build logs to find what triggered it
    echo "📦 Searching for 'pyarrow' in pip install output..."
    echo ""
    if gcloud builds log "$LATEST_BUILD" --region="$REGION" 2>/dev/null | grep -i "pyarrow" | head -n 30; then
      echo ""
      echo "⚠️  Found pyarrow references above!"
      echo "   Look for lines like: 'Collecting pyarrow (from <package-name>)'"
      echo "   This shows which package triggered pyarrow installation"
    else
      echo "   ✓ No 'pyarrow' found in build logs (might be a different error)"
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "💡 To see full build logs, run:"
    echo "   gcloud builds log $LATEST_BUILD --region=$REGION"
    echo ""
    echo "💡 Or view in Cloud Console:"
    echo "   https://console.cloud.google.com/cloud-build/builds;region=$REGION/$LATEST_BUILD?project=$PROJECT_ID"
    echo ""
  else
    echo "⚠️  Could not fetch Cloud Build logs (no builds found in region $REGION)"
    echo "   Check Cloud Console manually: https://console.cloud.google.com/cloud-build/builds?project=$PROJECT_ID"
  fi

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  # Cleanup will happen via trap, then exit with failure code
  exit $DEPLOY_EXIT_CODE
fi

# === SUCCESS PATH ===
# Cleanup will happen automatically via trap

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Service URL:"
gcloud run services describe "$SERVICE_NAME" --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)'
echo ""
echo "API Docs:"
echo "$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')/docs"
echo ""
echo "Health Check:"
echo "$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')/health"
