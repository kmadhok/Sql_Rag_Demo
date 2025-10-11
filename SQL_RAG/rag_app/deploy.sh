#!/bin/bash

# SQL RAG Application - Google Cloud Run Deployment Script
# This script automates the complete deployment process to Google Cloud Run

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=""
REGION="us-central1"
SERVICE_NAME="sql-rag-app"
REPOSITORY_NAME="sql-rag-repo"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if required tools are installed
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "Google Cloud CLI (gcloud) is not installed."
        print_status "Install it from: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed."
        print_status "Install it from: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to get or set project ID
setup_project() {
    if [ -z "$PROJECT_ID" ]; then
        # Try to get current project
        CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
        
        if [ -z "$CURRENT_PROJECT" ]; then
            print_error "No Google Cloud project is set."
            echo "Please run: gcloud config set project YOUR_PROJECT_ID"
            echo "Or set PROJECT_ID variable in this script."
            exit 1
        else
            PROJECT_ID="$CURRENT_PROJECT"
            print_status "Using current project: $PROJECT_ID"
        fi
    else
        print_status "Using configured project: $PROJECT_ID"
        gcloud config set project "$PROJECT_ID"
    fi
}

# Function to enable required APIs
enable_apis() {
    print_status "Enabling required Google Cloud APIs..."
    
    gcloud services enable \
        cloudbuild.googleapis.com \
        run.googleapis.com \
        artifactregistry.googleapis.com \
        secretmanager.googleapis.com \
        logging.googleapis.com \
        monitoring.googleapis.com
    
    print_success "APIs enabled successfully"
}

# Function to create Artifact Registry repository
create_artifact_repository() {
    print_status "Creating Artifact Registry repository..."
    
    # Check if repository already exists
    if gcloud artifacts repositories describe "$REPOSITORY_NAME" \
        --location="$REGION" >/dev/null 2>&1; then
        print_warning "Repository $REPOSITORY_NAME already exists"
    else
        gcloud artifacts repositories create "$REPOSITORY_NAME" \
            --repository-format=docker \
            --location="$REGION" \
            --description="SQL RAG Application Container Repository"
        print_success "Repository created successfully"
    fi
    
    # Configure Docker to use Artifact Registry
    gcloud auth configure-docker "${REGION}-docker.pkg.dev"
}

# Function to create secrets in Secret Manager
create_secrets() {
    print_status "Setting up secrets in Secret Manager..."
    
    # Check for OpenAI API key
    if [ -z "$OPENAI_API_KEY" ]; then
        print_warning "OPENAI_API_KEY environment variable not set"
        read -p "Enter your OpenAI API key: " -s OPENAI_API_KEY
        echo
    fi
    
    # Check for Gemini API key
    if [ -z "$GEMINI_API_KEY" ]; then
        print_warning "GEMINI_API_KEY environment variable not set"
        read -p "Enter your Gemini API key: " -s GEMINI_API_KEY
        echo
    fi
    
    # Create or update OpenAI API key secret
    if gcloud secrets describe openai-api-key >/dev/null 2>&1; then
        print_warning "OpenAI API key secret already exists, updating..."
        echo -n "$OPENAI_API_KEY" | gcloud secrets versions add openai-api-key --data-file=-
    else
        echo -n "$OPENAI_API_KEY" | gcloud secrets create openai-api-key --data-file=-
        print_success "OpenAI API key secret created"
    fi
    
    # Create or update Gemini API key secret
    if gcloud secrets describe gemini-api-key >/dev/null 2>&1; then
        print_warning "Gemini API key secret already exists, updating..."
        echo -n "$GEMINI_API_KEY" | gcloud secrets versions add gemini-api-key --data-file=-
    else
        echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
        print_success "Gemini API key secret created"
    fi
}

# Function to build and deploy the application
build_and_deploy() {
    print_status "Building and deploying the application..."
    
    # Build the Docker image using Cloud Build
    IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY_NAME}/${SERVICE_NAME}:latest"
    
    gcloud builds submit \
        --tag="$IMAGE_URL" \
        --timeout="20m" \
        .
    
    print_success "Image built successfully: $IMAGE_URL"
    
    # Deploy to Cloud Run
    print_status "Deploying to Cloud Run..."
    
    gcloud run deploy "$SERVICE_NAME" \
        --image="$IMAGE_URL" \
        --region="$REGION" \
        --platform=managed \
        --allow-unauthenticated \
        --port=8080 \
        --memory=2Gi \
        --cpu=2 \
        --max-instances=10 \
        --min-instances=0 \
        --concurrency=80 \
        --timeout=300 \
        --set-env-vars="PYTHONUNBUFFERED=1,STREAMLIT_SERVER_ENABLE_CORS=false,STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false,EMBEDDINGS_PROVIDER=openai" \
        --set-secrets="OPENAI_API_KEY=openai-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest" \
        --labels="app=sql-rag,environment=production"
    
    print_success "Deployment completed successfully"
}

# Function to get service URL
get_service_url() {
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)")
    
    print_success "Application deployed successfully!"
    echo
    echo "🌐 Service URL: $SERVICE_URL"
    echo "📊 Health Check: $SERVICE_URL/_stcore/health"
    echo
    echo "📝 To monitor your service:"
    echo "   gcloud run services logs tail $SERVICE_NAME --region=$REGION"
    echo
    echo "🔧 To update the service:"
    echo "   ./deploy.sh"
}

# Function to setup CI/CD with Cloud Build triggers
setup_cicd() {
    print_status "Setting up CI/CD with Cloud Build..."
    
    # Note: This requires GitHub integration to be set up manually
    print_warning "To set up automatic deployments from GitHub:"
    echo "1. Connect your GitHub repository to Cloud Build"
    echo "2. Run the following command:"
    echo "   gcloud builds triggers create github \\"
    echo "     --repo-name=your-repo-name \\"
    echo "     --repo-owner=your-github-username \\"
    echo "     --branch-pattern='^main$' \\"
    echo "     --build-config=cloudbuild.yaml"
}

# Main deployment function
main() {
    echo "🚀 SQL RAG Application - Google Cloud Run Deployment"
    echo "=================================================="
    echo
    
    check_prerequisites
    setup_project
    enable_apis
    create_artifact_repository
    create_secrets
    build_and_deploy
    get_service_url
    
    echo
    print_success "Deployment process completed!"
    
    # Offer to set up CI/CD
    read -p "Would you like to see CI/CD setup instructions? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_cicd
    fi
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "SQL RAG Application Deployment Script"
        echo
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --project-id   Set Google Cloud project ID"
        echo "  --region       Set deployment region (default: us-central1)"
        echo "  --service-name Set Cloud Run service name (default: sql-rag-app)"
        echo
        echo "Environment variables:"
        echo "  OPENAI_API_KEY  OpenAI API key (required)"
        echo "  GEMINI_API_KEY  Google Gemini API key (required)"
        echo
        echo "Examples:"
        echo "  $0"
        echo "  $0 --project-id my-project --region us-west1"
        exit 0
        ;;
    --project-id)
        PROJECT_ID="$2"
        shift 2
        ;;
    --region)
        REGION="$2"
        shift 2
        ;;
    --service-name)
        SERVICE_NAME="$2"
        shift 2
        ;;
    "")
        # No arguments, proceed with deployment
        ;;
    *)
        print_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

# Run the main deployment
main