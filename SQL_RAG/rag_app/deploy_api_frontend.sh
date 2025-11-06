#!/bin/bash

# SQL RAG API + Frontend - Cloud Build Deployment Script
# Deploys FastAPI backend and React frontend as two separate Cloud Run services

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Defaults (override via flags)
PROJECT_ID=""
REGION="us-central1"
BACKEND_SERVICE_NAME="sql-rag-api"
FRONTEND_SERVICE_NAME="sql-rag-frontend"
REPOSITORY_NAME="sql-rag-repo"

print_info()   { echo -e "${BLUE}[INFO]${NC} $1" >&2; }
print_ok()     { echo -e "${GREEN}[SUCCESS]${NC} $1" >&2; }
print_warn()   { echo -e "${YELLOW}[WARNING]${NC} $1" >&2; }
print_error()  { echo -e "${RED}[ERROR]${NC} $1" >&2; }

check_prereqs() {
  print_info "Checking prerequisites..."

  if ! command -v gcloud >/dev/null 2>&1; then
    print_error "Google Cloud CLI (gcloud) is not installed."
    echo "Install: https://cloud.google.com/sdk/docs/install"
    exit 1
  fi

  # No local Docker requirement; Cloud Build performs the build remotely.
  print_ok "Prerequisites check passed (Cloud Build only)"
}

setup_project() {
  if [[ -z "$PROJECT_ID" ]]; then
    local current
    current=$(gcloud config get-value project 2>/dev/null || true)
    if [[ -z "$current" ]]; then
      print_error "No Google Cloud project is set."
      echo "Run: gcloud config set project YOUR_PROJECT_ID"
      echo "Or pass --project-id flag to this script."
      exit 1
    fi
    PROJECT_ID="$current"
    print_info "Using current project: $PROJECT_ID"
  else
    print_info "Using configured project: $PROJECT_ID"
    gcloud config set project "$PROJECT_ID" >/dev/null
  fi
}

enable_apis() {
  print_info "Enabling required Google Cloud APIs..."
  gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com \
    firestore.googleapis.com \
    bigquery.googleapis.com
  print_ok "APIs enabled successfully"
}

create_artifact_repo() {
  print_info "Ensuring Artifact Registry repository exists..."
  if gcloud artifacts repositories describe "$REPOSITORY_NAME" --location="$REGION" >/dev/null 2>&1; then
    print_warn "Repository $REPOSITORY_NAME already exists"
  else
    gcloud artifacts repositories create "$REPOSITORY_NAME" \
      --repository-format=docker \
      --location="$REGION" \
      --description="SQL RAG Application Container Repository"
    print_ok "Repository created"
  fi
}

setup_firestore() {
  print_info "Setting up Firestore database..."

  # Check if Firestore database already exists
  if gcloud firestore databases describe --database='(default)' >/dev/null 2>&1; then
    print_warn "Firestore database already exists"
  else
    # Create Firestore database in Native mode for better performance
    print_info "Creating Firestore database in Native mode..."
    gcloud firestore databases create --database='(default)' --location="$REGION" --type=firestore-native
    print_ok "Firestore database created"
  fi
}

create_or_update_secrets() {
  print_info "Setting up secrets in Secret Manager..."

  local oa_key gem_key
  oa_key=${OPENAI_API_KEY:-}
  gem_key=${GEMINI_API_KEY:-}

  if [[ -z "$oa_key" ]]; then
    print_warn "OPENAI_API_KEY env var not set"
    read -r -s -p "Enter your OpenAI API key: " oa_key; echo
  fi

  if [[ -z "$gem_key" ]]; then
    print_warn "GEMINI_API_KEY env var not set"
    read -r -s -p "Enter your Gemini API key: " gem_key; echo
  fi

  if gcloud secrets describe openai-api-key >/dev/null 2>&1; then
    print_warn "openai-api-key exists; adding new version..."
    printf %s "$oa_key" | gcloud secrets versions add openai-api-key --data-file=- >/dev/null
  else
    printf %s "$oa_key" | gcloud secrets create openai-api-key --data-file=- >/dev/null
    print_ok "Created secret: openai-api-key"
  fi

  if gcloud secrets describe gemini-api-key >/dev/null 2>&1; then
    print_warn "gemini-api-key exists; adding new version..."
    printf %s "$gem_key" | gcloud secrets versions add gemini-api-key --data-file=- >/dev/null
  else
    printf %s "$gem_key" | gcloud secrets create gemini-api-key --data-file=- >/dev/null
    print_ok "Created secret: gemini-api-key"
  fi
}

grant_secret_access() {
  # Ensure the runtime service account can access Secret Manager, Firestore, and BigQuery
  print_info "Granting permissions to Cloud Run runtime SA..."
  local project_number runtime_sa
  project_number=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
  runtime_sa="${project_number}-compute@developer.gserviceaccount.com"

  # Grant Secret Manager access
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${runtime_sa}" \
    --role="roles/secretmanager.secretAccessor" >/dev/null 2>&1 || true
  print_ok "Ensured roles/secretmanager.secretAccessor for ${runtime_sa}"

  # Grant Firestore access for conversation persistence
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${runtime_sa}" \
    --role="roles/datastore.user" >/dev/null 2>&1 || true
  print_ok "Ensured roles/datastore.user for ${runtime_sa}"

  # Grant BigQuery job permissions for executing read-only queries
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${runtime_sa}" \
    --role="roles/bigquery.jobUser" >/dev/null 2>&1 || true
  print_ok "Ensured roles/bigquery.jobUser for ${runtime_sa}"

  echo "$runtime_sa"
}

build_and_deploy_backend() {
  print_info "Building and deploying FastAPI backend..."
  local image_url
  image_url="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY_NAME}/${BACKEND_SERVICE_NAME}:latest"

  # Build backend image using cloudbuild.api.yaml
  print_info "Building backend container with Cloud Build..."
  gcloud builds submit \
    --config "cloudbuild.api.yaml" \
    --substitutions "_REGION=${REGION},_REPOSITORY=${REPOSITORY_NAME},_IMAGE_NAME=${BACKEND_SERVICE_NAME}" \
    --timeout "20m" \
    .
  print_ok "Backend image built and pushed: $image_url"

  # Deploy backend to Cloud Run
  print_info "Deploying backend to Cloud Run..."
  local runtime_sa
  runtime_sa=$(grant_secret_access)

  gcloud run deploy "$BACKEND_SERVICE_NAME" \
    --image "$image_url" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --max-instances 10 \
    --min-instances 0 \
    --concurrency 80 \
    --timeout 300 \
    --service-account "$runtime_sa" \
    --set-env-vars "PYTHONUNBUFFERED=1,EMBEDDINGS_PROVIDER=openai,BIGQUERY_PROJECT_ID=${PROJECT_ID},BIGQUERY_DATASET=bigquery-public-data.thelook_ecommerce,CORS_ORIGINS=*" \
    --set-secrets "OPENAI_API_KEY=openai-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest" \
    --labels "app=sql-rag,component=backend,environment=production"

  print_ok "Backend deployment completed"

  # Get backend URL for frontend configuration
  local backend_url
  backend_url=$(gcloud run services describe "$BACKEND_SERVICE_NAME" --region "$REGION" --format='value(status.url)')
  echo "$backend_url"
}

build_and_deploy_frontend() {
  local backend_url="$1"
  print_info "Building and deploying React frontend..."
  local image_url
  image_url="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY_NAME}/${FRONTEND_SERVICE_NAME}:latest"

  # Build frontend image using cloudbuild.frontend.yaml with API URL as build arg
  print_info "Building frontend container with Cloud Build..."
  gcloud builds submit \
    --config "cloudbuild.frontend.yaml" \
    --substitutions "_REGION=${REGION},_REPOSITORY=${REPOSITORY_NAME},_IMAGE_NAME=${FRONTEND_SERVICE_NAME},_VITE_API_BASE_URL=${backend_url}" \
    --timeout "20m" \
    .
  print_ok "Frontend image built and pushed: $image_url"

  # Deploy frontend to Cloud Run
  print_info "Deploying frontend to Cloud Run..."
  local runtime_sa
  runtime_sa=$(grant_secret_access)

  gcloud run deploy "$FRONTEND_SERVICE_NAME" \
    --image "$image_url" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --cpu 1 \
    --max-instances 5 \
    --min-instances 0 \
    --concurrency 80 \
    --timeout 60 \
    --service-account "$runtime_sa" \
    --set-env-vars "VITE_API_BASE_URL=${backend_url}" \
    --labels "app=sql-rag,component=frontend,environment=production"

  print_ok "Frontend deployment completed"
}

update_backend_cors() {
  local frontend_url="$1"
  print_info "Updating backend CORS configuration for frontend URL..."

  # Update backend service with frontend URL in CORS_ORIGINS
  gcloud run services update "$BACKEND_SERVICE_NAME" \
    --region "$REGION" \
    --update-env-vars "CORS_ORIGINS=${frontend_url}" \
    --quiet

  print_ok "Backend CORS updated to allow: $frontend_url"
}

print_service_info() {
  local backend_url frontend_url
  backend_url=$(gcloud run services describe "$BACKEND_SERVICE_NAME" --region "$REGION" --format='value(status.url)')
  frontend_url=$(gcloud run services describe "$FRONTEND_SERVICE_NAME" --region "$REGION" --format='value(status.url)')

  print_ok "Deployment completed successfully!"
  echo
  echo "==============================================="
  echo "🎉 SQL RAG Application Deployed"
  echo "==============================================="
  echo
  echo "📱 Frontend (React):"
  echo "   URL: $frontend_url"
  echo "   Health: $frontend_url/health"
  echo
  echo "🔌 Backend (FastAPI):"
  echo "   URL: $backend_url"
  echo "   Health: $backend_url/health"
  echo "   API Docs: $backend_url/docs"
  echo
  echo "📊 Existing Streamlit App:"
  echo "   URL: $(gcloud run services describe sql-rag-app --region "$REGION" --format='value(status.url)' 2>/dev/null || echo 'Not deployed')"
  echo
  echo "==============================================="
  echo
  echo "📝 View logs:"
  echo "   Backend:  gcloud run services logs tail $BACKEND_SERVICE_NAME --region=$REGION"
  echo "   Frontend: gcloud run services logs tail $FRONTEND_SERVICE_NAME --region=$REGION"
  echo
  echo "🔧 Manage services:"
  echo "   gcloud run services list --region=$REGION"
  echo
}

usage() {
  cat <<EOF
SQL RAG API + Frontend - Cloud Build Deployment

Usage: $0 [options]

Options:
  --project-id <ID>           Google Cloud project ID (overrides gcloud config)
  --region <REGION>           Deployment region (default: us-central1)
  --backend-service <NAME>    Backend service name (default: sql-rag-api)
  --frontend-service <NAME>   Frontend service name (default: sql-rag-frontend)
  --repository <NAME>         Artifact Registry repo (default: sql-rag-repo)
  -h, --help                  Show this help

Environment variables (optional):
  OPENAI_API_KEY              OpenAI API key
  GEMINI_API_KEY              Google Gemini API key

Examples:
  $0 --project-id my-project
  OPENAI_API_KEY=sk-... GEMINI_API_KEY=... $0 --project-id my-project --region us-west1
EOF
}

main() {
  echo "🚀 SQL RAG API + Frontend - Cloud Build Deployment"
  echo "============================================================"
  echo

  check_prereqs
  setup_project
  enable_apis
  create_artifact_repo
  setup_firestore
  create_or_update_secrets

  # Deploy backend first
  local backend_url
  backend_url=$(build_and_deploy_backend)

  # Deploy frontend with backend URL
  build_and_deploy_frontend "$backend_url"

  # Get frontend URL
  local frontend_url
  frontend_url=$(gcloud run services describe "$FRONTEND_SERVICE_NAME" --region "$REGION" --format='value(status.url)')

  # Update backend CORS with frontend URL
  update_backend_cors "$frontend_url"

  # Print service info
  print_service_info

  echo
  print_ok "All deployment steps completed!"
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-id)
      PROJECT_ID="$2"; shift 2 ;;
    --region)
      REGION="$2"; shift 2 ;;
    --backend-service)
      BACKEND_SERVICE_NAME="$2"; shift 2 ;;
    --frontend-service)
      FRONTEND_SERVICE_NAME="$2"; shift 2 ;;
    --repository)
      REPOSITORY_NAME="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      print_error "Unknown option: $1"; echo; usage; exit 1 ;;
  esac
done

main
