#!/bin/bash
# SQL RAG Deployment - Pre-flight Checks
# Validates all prerequisites before deployment
# Exit code: 0 = all checks passed, 1 = one or more checks failed

set -e

echo "🔍 SQL RAG Deployment - Pre-flight Checks"
echo "=========================================="
echo ""

ERRORS=0
WARNINGS=0

# ============================================
# Check 1: Docker Desktop
# ============================================
echo "1️⃣  Checking Docker..."
if ! docker ps &>/dev/null; then
  echo "❌ Docker is not running"
  echo "   Action: Start Docker Desktop and wait 30 seconds for initialization"
  echo "   Command: open -a Docker (macOS)"
  echo ""
  ERRORS=$((ERRORS + 1))
else
  echo "✅ Docker is running"
fi

# ============================================
# Check 2: Google Cloud Authentication
# ============================================
echo "2️⃣  Checking Google Cloud authentication..."
ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || echo "")
if [ -z "$ACTIVE_ACCOUNT" ]; then
  echo "❌ Not authenticated with Google Cloud"
  echo "   Action: Run 'gcloud auth login'"
  echo ""
  ERRORS=$((ERRORS + 1))
else
  echo "✅ Google Cloud authenticated as: $ACTIVE_ACCOUNT"
fi

# ============================================
# Check 3: Google Cloud Project
# ============================================
echo "3️⃣  Checking Google Cloud project..."
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
EXPECTED_PROJECT="brainrot-453319"

if [ -z "$CURRENT_PROJECT" ]; then
  echo "❌ No Google Cloud project set"
  echo "   Action: Run 'gcloud config set project $EXPECTED_PROJECT'"
  echo ""
  ERRORS=$((ERRORS + 1))
elif [ "$CURRENT_PROJECT" != "$EXPECTED_PROJECT" ]; then
  echo "⚠️  Project is '$CURRENT_PROJECT' (expected: $EXPECTED_PROJECT)"
  echo "   Note: You can continue, but verify this is intentional"
  echo "   To change: gcloud config set project $EXPECTED_PROJECT"
  echo ""
  WARNINGS=$((WARNINGS + 1))
else
  echo "✅ Google Cloud project: $CURRENT_PROJECT"
fi

# ============================================
# Check 4: .env.deploy File
# ============================================
echo "4️⃣  Checking .env.deploy file..."
if [ ! -f .env.deploy ]; then
  echo "❌ .env.deploy file not found"
  echo "   Action: Create .env.deploy from template"
  echo "   Command: cp .env.deploy.example .env.deploy"
  echo "   Then edit .env.deploy to add your API keys"
  echo ""
  ERRORS=$((ERRORS + 1))
else
  echo "✅ .env.deploy exists"

  # Check for required environment variables
  echo "   Checking required API keys..."

  if ! grep -q "^GEMINI_API_KEY=" .env.deploy || grep -q "^GEMINI_API_KEY=your-" .env.deploy; then
    echo "   ❌ GEMINI_API_KEY is missing or not configured"
    echo "      Action: Add your Gemini API key to .env.deploy"
    echo "      Get from: https://makersuite.google.com/app/apikey"
    echo ""
    ERRORS=$((ERRORS + 1))
  else
    echo "   ✅ GEMINI_API_KEY configured"
  fi

  if ! grep -q "^OPENAI_API_KEY=" .env.deploy || grep -q "^OPENAI_API_KEY=your-" .env.deploy; then
    echo "   ❌ OPENAI_API_KEY is missing or not configured"
    echo "      Action: Add your OpenAI API key to .env.deploy"
    echo "      Get from: https://platform.openai.com/api-keys"
    echo ""
    ERRORS=$((ERRORS + 1))
  else
    echo "   ✅ OPENAI_API_KEY configured"
  fi

  if ! grep -q "^EMBEDDINGS_PROVIDER=" .env.deploy; then
    echo "   ⚠️  EMBEDDINGS_PROVIDER not set (will use default)"
    echo "      Recommended: Add 'EMBEDDINGS_PROVIDER=gemini' to .env.deploy"
    echo ""
    WARNINGS=$((WARNINGS + 1))
  else
    EMBEDDING_PROVIDER=$(grep "^EMBEDDINGS_PROVIDER=" .env.deploy | cut -d'=' -f2)
    echo "   ✅ EMBEDDINGS_PROVIDER: $EMBEDDING_PROVIDER"
  fi
fi

# ============================================
# Check 5: FAISS Vector Indices
# ============================================
echo "5️⃣  Checking FAISS vector indices..."
FAISS_DIR="faiss_indices/index_sample_queries_with_metadata_recovered"
if [ ! -d "$FAISS_DIR" ]; then
  echo "❌ FAISS indices not found at: $FAISS_DIR"
  echo "   Action: Generate embeddings first"
  echo "   Command: python standalone_embedding_generator.py --csv sample_queries_with_metadata.csv"
  echo ""
  ERRORS=$((ERRORS + 1))
else
  if [ -f "$FAISS_DIR/index.faiss" ] && [ -f "$FAISS_DIR/index.pkl" ]; then
    FAISS_SIZE=$(du -sh "$FAISS_DIR" | cut -f1)
    echo "✅ FAISS indices exist (size: $FAISS_SIZE)"
  else
    echo "❌ FAISS indices directory exists but index files are missing"
    echo "   Expected: index.faiss and index.pkl"
    echo "   Action: Regenerate embeddings"
    echo ""
    ERRORS=$((ERRORS + 1))
  fi
fi

# ============================================
# Check 6: Schema CSV
# ============================================
echo "6️⃣  Checking schema CSV..."
SCHEMA_CSV="data_new/thelook_ecommerce_schema.csv"
if [ ! -f "$SCHEMA_CSV" ]; then
  echo "❌ Schema CSV not found at: $SCHEMA_CSV"
  echo "   Action: Ensure schema file exists"
  echo ""
  ERRORS=$((ERRORS + 1))
else
  SCHEMA_SIZE=$(wc -l < "$SCHEMA_CSV" | tr -d ' ')
  echo "✅ Schema CSV exists ($SCHEMA_SIZE lines)"
fi

# ============================================
# Check 7: Deployment Scripts
# ============================================
echo "7️⃣  Checking deployment scripts..."
if [ ! -f deploy_api_simple.sh ]; then
  echo "❌ Backend deployment script not found: deploy_api_simple.sh"
  ERRORS=$((ERRORS + 1))
elif [ ! -x deploy_api_simple.sh ]; then
  echo "⚠️  Backend deployment script is not executable"
  echo "   Action: Run 'chmod +x deploy_api_simple.sh'"
  WARNINGS=$((WARNINGS + 1))
else
  echo "✅ Backend deployment script ready"
fi

if [ ! -f frontend/deploy_frontend_simple.sh ]; then
  echo "❌ Frontend deployment script not found: frontend/deploy_frontend_simple.sh"
  ERRORS=$((ERRORS + 1))
elif [ ! -x frontend/deploy_frontend_simple.sh ]; then
  echo "⚠️  Frontend deployment script is not executable"
  echo "   Action: Run 'chmod +x frontend/deploy_frontend_simple.sh'"
  WARNINGS=$((WARNINGS + 1))
else
  echo "✅ Frontend deployment script ready"
fi

# ============================================
# Final Summary
# ============================================
echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
  echo "✅ All pre-flight checks passed!"
  echo ""
  echo "Ready to deploy. Choose one:"
  echo ""
  echo "  Option 1: Deploy everything"
  echo "    $ ./deploy_all.sh"
  echo ""
  echo "  Option 2: Deploy step-by-step"
  echo "    $ ./deploy_api_simple.sh              # Backend (~5 min)"
  echo "    $ cd frontend && ./deploy_frontend_simple.sh  # Frontend (~8 min)"
  echo ""
  exit 0
elif [ $ERRORS -eq 0 ]; then
  echo "⚠️  All critical checks passed ($WARNINGS warnings)"
  echo ""
  echo "You can proceed with deployment, but review warnings above."
  echo ""
  exit 0
else
  echo "❌ $ERRORS critical issue(s) found"
  if [ $WARNINGS -gt 0 ]; then
    echo "⚠️  $WARNINGS warning(s)"
  fi
  echo ""
  echo "Fix the issues above before deploying."
  echo ""
  echo "Need help?"
  echo "  - See DEPLOYMENT.md for detailed setup instructions"
  echo "  - See QUICKSTART.md for a minimal deployment guide"
  echo "  - Check .env.deploy.example for environment variable template"
  echo ""
  exit 1
fi
