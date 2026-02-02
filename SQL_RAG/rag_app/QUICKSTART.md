# SQL RAG - Quick Start Deployment

**Ultra-concise deployment guide for the 2-tab SQL RAG application.**

For detailed instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Prerequisites

### Required Tools
- ✅ Docker Desktop (running)
- ✅ Google Cloud SDK (authenticated)
- ✅ API Keys (Gemini + OpenAI)

### Setup
```bash
# 1. Authenticate with Google Cloud
gcloud auth login
gcloud config set project brainrot-453319

# 2. Create environment file
cp .env.deploy.example .env.deploy
# Edit .env.deploy and add your API keys

# 3. Start Docker Desktop
open -a Docker
```

---

## Deploy (Option 1: One Command)

```bash
cd rag_app
./deploy_all.sh
```

**Time:** ~13 minutes total

---

## Deploy (Option 2: Step-by-Step)

```bash
# Backend (~5 minutes)
cd rag_app
./deploy_api_simple.sh

# Frontend (~8 minutes)
cd frontend
./deploy_frontend_simple.sh
```

---

## Deployed URLs

**Frontend (2-Tab UI):**
https://sql-rag-frontend-simple-481433773942.us-central1.run.app

**Backend (API):**
https://sql-rag-api-simple-481433773942.us-central1.run.app

**API Docs:**
https://sql-rag-api-simple-481433773942.us-central1.run.app/docs

---

## Verify Deployment

```bash
# Test backend health
curl https://sql-rag-api-simple-481433773942.us-central1.run.app/health

# Open frontend in browser
open https://sql-rag-frontend-simple-481433773942.us-central1.run.app
```

**Expected:**
- ✅ 2 tabs visible: Chat | Dashboard
- ✅ Hero banner: "Explore Data with Natural Language"
- ✅ Backend health: `{"status":"ok"}`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Docker daemon not running` | Start Docker Desktop, wait 30s |
| `gcloud: command not found` | Install Google Cloud SDK |
| `Backend service not found` | Deploy backend first |
| `.env.deploy` missing API keys | Edit file and add real API keys |
| Permission denied on scripts | `chmod +x *.sh` |

---

## Common Commands

```bash
# Run pre-flight checks
./preflight_check.sh

# View backend logs
gcloud run services logs read sql-rag-api-simple --region us-central1

# View frontend logs
gcloud run services logs read sql-rag-frontend-simple --region us-central1

# Redeploy backend only
./deploy_api_simple.sh

# Redeploy frontend only
cd frontend && ./deploy_frontend_simple.sh
```

---

## Deployment Scripts

**⚠️ Important:** This directory contains 7 `.sh` scripts. **Only use these 4:**

| Script | Use For |
|--------|---------|
| `deploy_all.sh` | Deploy everything (recommended) |
| `deploy_api_simple.sh` | Backend only |
| `frontend/deploy_frontend_simple.sh` | Frontend only |
| `preflight_check.sh` | Validate setup before deploying |

**Ignore these legacy scripts:**
- `deploy.sh`, `deploy_api_frontend.sh`, `deploy_cloudbuild.sh` (deprecated)

## Project Structure

```
rag_app/
├── deploy_all.sh              ✅ One-command deployment
├── deploy_api_simple.sh       ✅ Backend deployment
├── preflight_check.sh         ✅ Prerequisites validator
├── .env.deploy.example        # Environment template
├── .env.deploy                # Your API keys (git-ignored)
└── frontend/
    └── deploy_frontend_simple.sh  ✅ Frontend deployment
```

---

## Resources

- **Detailed Guide:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **Environment Template:** [.env.deploy.example](.env.deploy.example)
- **Gemini API Key:** https://makersuite.google.com/app/apikey
- **OpenAI API Key:** https://platform.openai.com/api-keys

---

**Need help?** See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive troubleshooting and configuration options.
