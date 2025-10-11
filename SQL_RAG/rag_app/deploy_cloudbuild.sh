#!/bin/bash

# SQL RAG Application - Cloud Build Only Deployment Script (no local Docker auth)
# This script deploys to Google Cloud Run using Cloud Build and Artifact Registry
# without requiring local Docker or docker auth configuration.

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
SERVICE_NAME="sql-rag-app"
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
    firestore.googleapis.com
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
  # Intentionally skipping: gcloud auth configure-docker
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
  # Ensure the runtime service account can access Secret Manager and Firestore
  print_info "Granting permissions to Cloud Run runtime SA..."
  local project_number runtime_sa
  project_number=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
  runtime_sa="${project_number}-compute@developer.gserviceaccount.com"

  # Grant Secret Manager access; ignore if already granted
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${runtime_sa}" \
    --role="roles/secretmanager.secretAccessor" >/dev/null 2>&1 || true
  print_ok "Ensured roles/secretmanager.secretAccessor for ${runtime_sa}"

  # Grant Firestore access for conversation persistence; ignore if already granted
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${runtime_sa}" \
    --role="roles/datastore.user" >/dev/null 2>&1 || true
  print_ok "Ensured roles/datastore.user for ${runtime_sa}"

  echo "$runtime_sa"
}

build_and_deploy() {
  print_info "Building container image with Cloud Build..."
  local image_url
  image_url="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY_NAME}/${SERVICE_NAME}:latest"

  gcloud builds submit \
    --tag "$image_url" \
    --timeout "20m" \
    .
  print_ok "Image built and pushed: $image_url"

  print_info "Deploying to Cloud Run..."
  local runtime_sa
  runtime_sa=$(grant_secret_access)

  gcloud run deploy "$SERVICE_NAME" \
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
    --set-env-vars "PYTHONUNBUFFERED=1,STREAMLIT_SERVER_ENABLE_CORS=false,STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false,EMBEDDINGS_PROVIDER=openai" \
    --set-secrets "OPENAI_API_KEY=openai-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest" \
    --labels "app=sql-rag,environment=production"

  print_ok "Deployment completed"
}

print_service_info() {
  local url
  url=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')
  print_ok "Application deployed successfully!"
  echo
  echo "Service URL: $url"
  echo "Health Check: $url/_stcore/health"
  echo
  echo "Tail logs: gcloud run services logs tail $SERVICE_NAME --region=$REGION"
}

usage() {
  cat <<EOF
SQL RAG Application - Cloud Build Only Deployment

Usage: $0 [options]

Options:
  --project-id <ID>     Google Cloud project ID (overrides gcloud config)
  --region <REGION>     Deployment region (default: us-central1)
  --service-name <NAME> Cloud Run service name (default: sql-rag-app)
  -h, --help            Show this help

Environment variables (optional):
  OPENAI_API_KEY        OpenAI API key
  GEMINI_API_KEY        Google Gemini API key

Examples:
  $0 --project-id my-project
  OPENAI_API_KEY=sk-... GEMINI_API_KEY=... $0 --project-id my-project --region us-west1
EOF
}

main() {
  echo "🚀 SQL RAG Application - Cloud Build Deployment (No Docker Auth)"
  echo "=============================================================="
  echo

  check_prereqs
  setup_project
  enable_apis
  create_artifact_repo
  setup_firestore
  create_or_update_secrets
  build_and_deploy
  print_service_info

  echo
  print_ok "Deployment process completed!"
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-id)
      PROJECT_ID="$2"; shift 2 ;;
    --region)
      REGION="$2"; shift 2 ;;
    --service-name)
      SERVICE_NAME="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      print_error "Unknown option: $1"; echo; usage; exit 1 ;;
  esac
done

main
