#!/bin/bash
# SQL RAG - Complete Deployment (Backend + Frontend)
# Deploys both services to Google Cloud Run in sequence

set -e  # Exit on any error

echo "🚀 SQL RAG - Complete Deployment"
echo "================================="
echo ""

# ============================================
# Step 0: Show current git context
# ============================================
if command -v git &>/dev/null && git rev-parse --git-dir &>/dev/null 2>&1; then
  CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
  LAST_COMMIT=$(git log -1 --oneline 2>/dev/null || echo "unknown")

  echo "📋 Deployment Context"
  echo "─────────────────────"
  echo "Branch: $CURRENT_BRANCH"
  echo "Commit: $LAST_COMMIT"
  echo ""

  echo "⚠️  This will deploy the current state of your code to Cloud Run."
  read -p "Continue with deployment? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled by user"
    exit 0
  fi
  echo ""
fi

# ============================================
# Step 1: Run pre-flight checks
# ============================================
echo "Step 0/2: Pre-flight Checks"
echo "─────────────────────────────"

if [ -f ./preflight_check.sh ]; then
  if ! ./preflight_check.sh; then
    echo ""
    echo "❌ Pre-flight checks failed"
    echo "   Fix the issues above before deploying"
    exit 1
  fi
else
  echo "⚠️  preflight_check.sh not found - skipping validation"
  echo "   (Deployment may fail if prerequisites are missing)"
  echo ""
  read -p "Continue anyway? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    exit 0
  fi
fi

echo ""
echo "=========================================="
echo ""

# ============================================
# Step 2: Deploy Backend
# ============================================
echo "Step 1/2: Deploying Backend API"
echo "─────────────────────────────────"
echo "Service: sql-rag-api-simple"
echo "Method: Buildpack (auto-detected Python/FastAPI)"
echo "Estimated time: ~5 minutes"
echo ""

START_BACKEND=$(date +%s)

if [ ! -f ./deploy_api_simple.sh ]; then
  echo "❌ Backend deployment script not found: ./deploy_api_simple.sh"
  exit 1
fi

# Deploy backend
./deploy_api_simple.sh

END_BACKEND=$(date +%s)
BACKEND_DURATION=$((END_BACKEND - START_BACKEND))

echo ""
echo "✅ Backend deployed in ${BACKEND_DURATION}s"
echo ""
echo "=========================================="
echo ""

# ============================================
# Step 3: Deploy Frontend
# ============================================
echo "Step 2/2: Deploying Frontend UI"
echo "────────────────────────────────"
echo "Service: sql-rag-frontend-simple"
echo "Method: Docker (multi-stage build with Vite)"
echo "Estimated time: ~8 minutes"
echo ""

START_FRONTEND=$(date +%s)

if [ ! -f frontend/deploy_frontend_simple.sh ]; then
  echo "❌ Frontend deployment script not found: frontend/deploy_frontend_simple.sh"
  exit 1
fi

# Deploy frontend (script expects to be run from rag_app directory)
cd frontend
./deploy_frontend_simple.sh
cd ..

END_FRONTEND=$(date +%s)
FRONTEND_DURATION=$((END_FRONTEND - START_FRONTEND))

echo ""
echo "✅ Frontend deployed in ${FRONTEND_DURATION}s"
echo ""

# ============================================
# Final Summary
# ============================================
TOTAL_DURATION=$((END_FRONTEND - START_BACKEND))
MINUTES=$((TOTAL_DURATION / 60))
SECONDS=$((TOTAL_DURATION % 60))

echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "⏱️  Total time: ${MINUTES}m ${SECONDS}s"
echo "   Backend: ${BACKEND_DURATION}s"
echo "   Frontend: ${FRONTEND_DURATION}s"
echo ""
echo "🌐 Deployed Services"
echo "────────────────────"
echo ""
echo "Frontend (React UI):"
echo "  https://sql-rag-frontend-simple-481433773942.us-central1.run.app"
echo ""
echo "Backend (FastAPI):"
echo "  https://sql-rag-api-simple-481433773942.us-central1.run.app"
echo ""
echo "API Docs:"
echo "  https://sql-rag-api-simple-481433773942.us-central1.run.app/docs"
echo ""
echo "=========================================="
echo ""
echo "🧪 Next Steps"
echo "─────────────"
echo "1. Open the frontend URL in your browser"
echo "2. Verify the 2-tab UI is visible (Chat | Dashboard)"
echo "3. Test Chat tab: Ask 'What tables are available?'"
echo "4. Test Dashboard tab: Browse saved queries"
echo ""
echo "📊 Monitor Deployment"
echo "────────────────────"
echo "Backend logs:"
echo "  gcloud run services logs read sql-rag-api-simple --region us-central1"
echo ""
echo "Frontend logs:"
echo "  gcloud run services logs read sql-rag-frontend-simple --region us-central1"
echo ""
echo "Happy querying! 🎉"
echo ""
