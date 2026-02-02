# SQL RAG Application - Deployment Guide

**Complete deployment instructions for the 2-tab SQL RAG application on Google Cloud Run.**

---

## Table of Contents

1. [Deployment Scripts Overview](#deployment-scripts-overview)
2. [Prerequisites](#prerequisites)
3. [First-Time Setup](#first-time-setup)
4. [Deployment Options](#deployment-options)
5. [Step-by-Step Deployment](#step-by-step-deployment)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Configuration](#advanced-configuration)
9. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Deployment Scripts Overview

**⚠️ Important:** This project contains multiple deployment scripts. **Only use the scripts marked ✅ below.**

If you run `ls *.sh` in the `rag_app/` directory, you'll see 7 scripts. Here's what each one does:

### ✅ Current Scripts (Use These)

| Script | Location | Purpose | When to Use |
|--------|----------|---------|-------------|
| **deploy_all.sh** | `rag_app/` | Deploy backend + frontend together | First deployment or complete updates |
| **deploy_api_simple.sh** | `rag_app/` | Deploy backend (FastAPI) only | Backend code changes |
| **deploy_frontend_simple.sh** | `rag_app/frontend/` | Deploy frontend (React) only | Frontend code changes |
| **preflight_check.sh** | `rag_app/` | Validate prerequisites before deployment | Before any deployment (recommended) |

### ⚠️ Legacy Scripts (Do Not Use)

| Script | Status | Notes |
|--------|--------|-------|
| **deploy.sh** | Deprecated | Old combined deployment. Use `deploy_all.sh` instead. |
| **deploy_api_frontend.sh** | Deprecated | Old combined deployment. Use `deploy_all.sh` instead. |
| **deploy_cloudbuild.sh** | Deprecated | Old Cloud Build method. Use `deploy_api_simple.sh` instead. |

**Why multiple scripts exist:** This project evolved through different deployment approaches (buildpacks, Docker, Cloud Build). The legacy scripts remain for backward compatibility but should **not** be used for new deployments.

**Quick Decision Guide:**
- 👉 First time deploying? → Use `deploy_all.sh`
- 👉 Only changed backend code? → Use `deploy_api_simple.sh`
- 👉 Only changed frontend code? → Use `cd frontend && deploy_frontend_simple.sh`
- 👉 Not sure if you're ready? → Run `preflight_check.sh` first

---

## Prerequisites

### Required Tools

| Tool | Version | Purpose | Installation |
|------|---------|---------|--------------|
| **Docker Desktop** | Latest | Frontend image building | [docker.com](https://www.docker.com/products/docker-desktop) |
| **Google Cloud SDK** | Latest | Cloud Run deployment | [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install) |
| **Git** | Any | Version control | Included with macOS/Linux |

**For local development only:**
- Node.js 20+ (frontend dev server)
- Python 3.11+ (backend dev server)

### Required Accounts & Credentials

1. **Google Cloud Project**
   - Project ID: `brainrot-453319` (or your own project)
   - Billing enabled
   - APIs enabled: Cloud Run, Cloud Build, Artifact Registry

2. **Gemini API Key**
   - For LLM-based SQL generation
   - Get from: https://makersuite.google.com/app/apikey

3. **OpenAI API Key**
   - For text embeddings (primary embedding provider)
   - Get from: https://platform.openai.com/api-keys

### Required Data Files

These files must exist in the `rag_app/` directory:

- ✅ `faiss_indices/index_sample_queries_with_metadata_recovered/`
  - `index.faiss` - Vector embeddings
  - `index.pkl` - Metadata
- ✅ `data_new/thelook_ecommerce_schema.csv` - Database schema
- ✅ `sample_queries_with_metadata.csv` - Sample queries

---

## First-Time Setup

### 1. Install Prerequisites

**Install Docker Desktop:**
```bash
# macOS
brew install --cask docker
# Or download from: https://www.docker.com/products/docker-desktop

# Start Docker Desktop
open -a Docker
```

**Install Google Cloud SDK:**
```bash
# macOS
brew install google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash
exec -l $SHELL  # Restart shell

# Verify installation
gcloud --version
```

### 2. Authenticate with Google Cloud

```bash
# Login to Google Cloud
gcloud auth login

# Set your project
gcloud config set project brainrot-453319

# Verify authentication
gcloud auth list
gcloud config get-value project
```

### 3. Configure Environment Variables

**Create `.env.deploy` from template:**
```bash
cd rag_app
cp .env.deploy.example .env.deploy
```

**Edit `.env.deploy` and add your API keys:**
```bash
# Open in your editor
nano .env.deploy
# Or: code .env.deploy (VS Code)
# Or: vim .env.deploy
```

**Minimum required configuration:**
```bash
GEMINI_API_KEY=AIzaSy...your-actual-key-here
OPENAI_API_KEY=sk-proj-...your-actual-key-here
EMBEDDINGS_PROVIDER=gemini
GENAI_CLIENT_MODE=api
```

**Save and close the file.**

⚠️ **Important:** `.env.deploy` is git-ignored. Never commit API keys to version control!

### 4. Verify Prerequisites

Run the automated pre-flight check:
```bash
./preflight_check.sh
```

**Expected output:**
```
✅ Docker is running
✅ Google Cloud authenticated
✅ Google Cloud project: brainrot-453319
✅ .env.deploy exists
   ✅ GEMINI_API_KEY configured
   ✅ OPENAI_API_KEY configured
✅ FAISS indices exist
✅ Schema CSV exists
✅ Deployment scripts ready

✅ All pre-flight checks passed!
```

If any checks fail, follow the suggested actions before proceeding.

---

## Deployment Options

### Option 1: One-Command Deployment (Recommended)

Deploy both backend and frontend with a single command:

```bash
./deploy_all.sh
```

**What it does:**
1. Runs pre-flight checks
2. Deploys backend to Cloud Run (~5 minutes)
3. Deploys frontend to Cloud Run (~8 minutes)
4. Shows deployed URLs

**Total time:** ~13 minutes

---

### Option 2: Step-by-Step Deployment

Deploy backend and frontend separately:

```bash
# Step 1: Deploy backend
./deploy_api_simple.sh

# Step 2: Deploy frontend
cd frontend
./deploy_frontend_simple.sh
```

**Use this when:**
- You only need to update one service
- You want more control over the deployment process
- Debugging deployment issues

---

## Step-by-Step Deployment

### Backend Deployment

**Script:** `deploy_api_simple.sh`
**Time:** ~5 minutes
**Method:** Buildpack (auto-detects Python/FastAPI)

```bash
cd /path/to/SQL_RAG/rag_app
./deploy_api_simple.sh
```

**What happens:**
1. Loads API keys from `.env.deploy`
2. Validates `requirements.txt` (checks for problematic dependencies)
3. Temporarily hides Dockerfiles (forces buildpack detection)
4. Uploads source code to Cloud Build
5. Buildpacks auto-detect Python + FastAPI from `Procfile`
6. Builds and deploys container to Cloud Run
7. Restores Dockerfiles

**Output:**
```
✅ Deployment complete!

Service URL:
https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app

API Docs:
https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app/docs

Health Check:
https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app/health
```

**Test the backend:**
```bash
curl https://sql-rag-api-simple-481433773942.us-central1.run.app/health
```

**Expected response:**
```json
{
  "status": "ok",
  "vector_store": true,
  "schema_manager": true,
  "lookml": true,
  "bigquery_executor": true
}
```

---

### Frontend Deployment

**Script:** `frontend/deploy_frontend_simple.sh`
**Time:** ~8 minutes
**Method:** Docker (multi-stage build)

**Important:** Must run from `rag_app/` directory (not `rag_app/frontend/`)

```bash
cd /path/to/SQL_RAG/rag_app/frontend
./deploy_frontend_simple.sh
```

**What happens:**
1. Pre-flight checks:
   - Verifies Docker is running
   - Checks backend service exists and is healthy
   - Tests backend query endpoint
2. Fetches backend URL from Cloud Run
3. Builds Docker image with Vite (includes 2-tab UI)
   - Build arg: `VITE_API_BASE_URL=<backend-url>`
   - Multi-stage build: Node.js → Nginx
4. Pushes image to Artifact Registry
5. Deploys to Cloud Run

**Output:**
```
✅ Deployment complete!

Frontend URL:
https://sql-rag-frontend-simple-orvqbubh7q-uc.a.run.app

Backend URL:
https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app
```

---

## Verification

### 1. Test Backend Health

```bash
curl https://sql-rag-api-simple-481433773942.us-central1.run.app/health | python -m json.tool
```

**Expected:**
```json
{
    "status": "ok",
    "vector_store": true,
    "schema_manager": true,
    "lookml": true,
    "bigquery_executor": true
}
```

### 2. Test Backend Query

```bash
curl -X POST https://sql-rag-api-simple-481433773942.us-central1.run.app/query/quick \
  -H "Content-Type: application/json" \
  -d '{"question":"What tables are available?","llm_model":"gemini-2.5-flash","k":5}'
```

**Expected:** JSON response with list of tables

### 3. Test Frontend

**Open in browser:**
https://sql-rag-frontend-simple-481433773942.us-central1.run.app

**Verify:**
- ✅ Page loads (no errors in browser console)
- ✅ 2 tabs visible: **Chat** and **Dashboard**
- ✅ Hero banner: "Explore Data with Natural Language"
- ✅ Chat tab is active by default

### 4. End-to-End Test

**In the Chat tab:**
1. Type: "What tables are available?"
2. Click Send or press Enter
3. Wait for response (~2-3 seconds)

**Expected:**
- Response lists 7 tables from `thelook_ecommerce` dataset
- No error messages

**Try SQL generation:**
1. Type: "@create Show me top 10 products by revenue"
2. Click Send
3. Wait for response (~5-8 seconds)

**Expected:**
- SQL query generated
- Execute button appears
- Can click Execute to run query on BigQuery

---

## Troubleshooting

### Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| **Docker not running** | `Cannot connect to Docker daemon` | 1. Start Docker Desktop<br>2. Wait 30 seconds for initialization<br>3. Verify with `docker ps` |
| **Not authenticated** | `gcloud: ERROR: (gcloud...) not authenticated` | Run `gcloud auth login` |
| **Wrong project** | Deployment goes to wrong project | Run `gcloud config set project brainrot-453319` |
| **Missing .env.deploy** | Warning about missing file | 1. `cp .env.deploy.example .env.deploy`<br>2. Edit and add API keys |
| **Invalid API keys** | Backend fails to start, 401 errors | 1. Verify keys in `.env.deploy`<br>2. Test keys with curl<br>3. Regenerate if needed |
| **Backend not found** | Frontend pre-flight check fails | Deploy backend first: `./deploy_api_simple.sh` |
| **Dockerfile not found** | Frontend build fails | Run script from `frontend/` directory |
| **Base image conflict** | `--clear-base-image` error | Script handles this automatically |
| **Port 3000 in use** | Vite dev server fails | Script auto-selects next available port |
| **Permission denied** | Cannot execute script | `chmod +x deploy_*.sh preflight_check.sh deploy_all.sh` |

### Detailed Troubleshooting

#### Backend Fails to Deploy

**Check build logs:**
```bash
# Find most recent build
gcloud builds list --limit=1

# View logs for specific build
gcloud builds log <BUILD_ID>
```

**Common backend issues:**
- Missing dependencies in `requirements.txt`
- Pyarrow version conflicts (should be commented out)
- Invalid API keys in `.env.deploy`
- FAISS indices missing or corrupted

#### Frontend Fails to Build

**Check Docker build output:**
```bash
# Rebuild locally to see errors
cd frontend
docker build . --build-arg VITE_API_BASE_URL=http://localhost:8080
```

**Common frontend issues:**
- Docker not running
- npm dependencies have vulnerabilities (warnings are OK)
- Backend URL not reachable
- Build arg missing

#### Backend Starts but Returns Errors

**View live logs:**
```bash
gcloud run services logs read sql-rag-api-simple --region us-central1 --limit 50
```

**Check for:**
- Embedding dimension mismatch (wrong `EMBEDDINGS_PROVIDER`)
- Vector store not initialized
- BigQuery permissions issues
- API rate limits

#### Frontend Loads but Can't Connect to Backend

**Check browser console:**
1. Open Developer Tools (F12)
2. Look for CORS errors or 404s

**Common causes:**
- Backend URL hardcoded incorrectly
- CORS not configured (`CORS_ORIGINS=*` should be in backend env vars)
- Backend service is down

**Test backend directly:**
```bash
curl https://sql-rag-api-simple-481433773942.us-central1.run.app/health
```

---

## Advanced Configuration

### Custom Project ID

To deploy to a different Google Cloud project:

1. **Update project ID in scripts:**
```bash
# In deploy_api_simple.sh
PROJECT_ID="your-project-id"

# In frontend/deploy_frontend_simple.sh
PROJECT_ID="your-project-id"
```

2. **Set gcloud config:**
```bash
gcloud config set project your-project-id
```

3. **Update frontend URLs after deployment**

### Using Vertex AI Instead of Public API

To use Vertex AI with service account authentication:

**Update `.env.deploy`:**
```bash
GENAI_CLIENT_MODE=sdk
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
# Remove or comment out: GEMINI_API_KEY
```

**Ensure service account has permissions:**
- Vertex AI User
- BigQuery Data Viewer
- BigQuery Job User

### Change Embedding Provider

**Important:** Embedding provider must match the FAISS indices!

**To switch from Gemini to OpenAI embeddings:**

1. **Regenerate FAISS indices:**
```bash
cd rag_app
export EMBEDDINGS_PROVIDER=openai
python standalone_embedding_generator.py --csv sample_queries_with_metadata.csv
```

2. **Update `.env.deploy`:**
```bash
EMBEDDINGS_PROVIDER=openai
```

3. **Redeploy backend**

### Resource Configuration

**Backend resources (in `deploy_api_simple.sh`):**
```bash
MEMORY="2Gi"   # Memory allocation
CPU="2"        # CPU count
MAX_INSTANCES="10"  # Auto-scaling limit
```

**Frontend resources (in `frontend/deploy_frontend_simple.sh`):**
```bash
MEMORY="512Mi"
CPU="1"
MAX_INSTANCES="10"
```

**To change:**
1. Edit the deployment script
2. Redeploy service

---

## Monitoring & Maintenance

### View Logs

**Backend logs:**
```bash
# Real-time streaming
gcloud run services logs tail sql-rag-api-simple --region us-central1

# Last 50 entries
gcloud run services logs read sql-rag-api-simple --region us-central1 --limit 50

# Filter by severity
gcloud run services logs read sql-rag-api-simple --region us-central1 --log-filter='severity>=ERROR'
```

**Frontend logs:**
```bash
gcloud run services logs read sql-rag-frontend-simple --region us-central1 --limit 50
```

### Service Information

**Get service details:**
```bash
# Backend
gcloud run services describe sql-rag-api-simple --region us-central1

# Frontend
gcloud run services describe sql-rag-frontend-simple --region us-central1
```

**Check revisions:**
```bash
# List all revisions
gcloud run revisions list --service sql-rag-api-simple --region us-central1

# Rollback to previous revision (if needed)
gcloud run services update-traffic sql-rag-api-simple \
  --to-revisions REVISION_NAME=100 \
  --region us-central1
```

### Cost Monitoring

**Estimate costs:**
- Backend: ~$5-10/month (light usage)
- Frontend: ~$2-5/month (light usage)
- Artifact Registry: ~$1-2/month
- **Total:** ~$8-17/month

**View actual costs:**
```bash
# Cloud Run costs
gcloud billing accounts list
gcloud beta billing accounts describe <ACCOUNT_ID>
```

Or visit: https://console.cloud.google.com/billing

### Update Deployment

**To deploy code changes:**

```bash
# Option 1: Redeploy everything
./deploy_all.sh

# Option 2: Update backend only
./deploy_api_simple.sh

# Option 3: Update frontend only
cd frontend && ./deploy_frontend_simple.sh
```

**To update environment variables:**

1. Edit `.env.deploy`
2. Redeploy backend: `./deploy_api_simple.sh`

(Frontend env vars are baked into the build, so rebuild is required)

---

## Deployment Flowchart

```
┌─────────────────────────────────────────┐
│  Start: First time deploying?           │
└────────────┬────────────────────────────┘
             │
             ├─ Yes ──> Follow "First-Time Setup"
             │           - Install tools
             │           - Authenticate gcloud
             │           - Create .env.deploy
             │           - Run preflight_check.sh
             │
             ├─ No  ──> Verify prerequisites
             │           - Docker running?
             │           - gcloud authenticated?
             │
┌────────────▼────────────────────────────┐
│  Choose Deployment Option               │
├─────────────────────────────────────────┤
│  A. One-command: ./deploy_all.sh        │
│  B. Step-by-step: Deploy backend first  │
└────────────┬────────────────────────────┘
             │
         ┌───┴───┐
         │   A   │ One-Command
         └───┬───┘
             │
┌────────────▼────────────────────────────┐
│  ./deploy_all.sh                        │
│  ├─ Pre-flight checks                   │
│  ├─ Deploy backend (~5 min)             │
│  └─ Deploy frontend (~8 min)            │
└────────────┬────────────────────────────┘
             │
             └────┐
                  │
         ┌────────▼──────────┐
         │   B   │ Step-by-Step
         └────────┬──────────┘
                  │
     ┌────────────▼────────────────────────────┐
     │  Step 1: Deploy Backend                 │
     │  $ ./deploy_api_simple.sh               │
     │  ⏱️  ~5 minutes                          │
     │  ✅ Backend URL displayed                │
     └────────────┬────────────────────────────┘
                  │
     ┌────────────▼────────────────────────────┐
     │  Step 2: Deploy Frontend                │
     │  $ cd frontend                           │
     │  $ ./deploy_frontend_simple.sh           │
     │  ⏱️  ~8 minutes                          │
     │  ✅ Frontend URL displayed               │
     └────────────┬────────────────────────────┘
                  │
     ┌────────────▼────────────────────────────┐
     │  ✅ Deployment Complete!                 │
     │                                          │
     │  Frontend:                               │
     │  https://sql-rag-frontend-simple-*.run.app│
     │                                          │
     │  Backend:                                │
     │  https://sql-rag-api-simple-*.run.app   │
     └────────────┬────────────────────────────┘
                  │
     ┌────────────▼────────────────────────────┐
     │  Verification                            │
     │  1. Test backend: curl /health           │
     │  2. Open frontend in browser             │
     │  3. Verify 2 tabs: Chat | Dashboard      │
     │  4. Test query: "What tables are there?" │
     └──────────────────────────────────────────┘
```

---

## Quick Reference

### Deployed URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend UI | https://sql-rag-frontend-simple-481433773942.us-central1.run.app | User interface |
| Backend API | https://sql-rag-api-simple-481433773942.us-central1.run.app | API server |
| API Docs | https://sql-rag-api-simple-481433773942.us-central1.run.app/docs | Interactive API docs |
| Health Check | https://sql-rag-api-simple-481433773942.us-central1.run.app/health | Service status |

### Useful Commands

```bash
# Deploy everything
./deploy_all.sh

# Deploy backend only
./deploy_api_simple.sh

# Deploy frontend only
cd frontend && ./deploy_frontend_simple.sh

# Pre-flight checks
./preflight_check.sh

# View backend logs
gcloud run services logs read sql-rag-api-simple --region us-central1 --limit 50

# View frontend logs
gcloud run services logs read sql-rag-frontend-simple --region us-central1 --limit 50

# Test backend health
curl https://sql-rag-api-simple-481433773942.us-central1.run.app/health

# Open frontend
open https://sql-rag-frontend-simple-481433773942.us-central1.run.app
```

---

## Need Help?

- **Quick Start:** See [QUICKSTART.md](QUICKSTART.md)
- **Environment Template:** See [.env.deploy.example](.env.deploy.example)
- **Project Documentation:** See main [README.md](../README.md)
- **Gemini API Docs:** https://ai.google.dev/gemini-api/docs
- **OpenAI API Docs:** https://platform.openai.com/docs
- **Google Cloud Run Docs:** https://cloud.google.com/run/docs

---

**Last Updated:** 2026-01-31
**Version:** 2-Tab UI Deployment
