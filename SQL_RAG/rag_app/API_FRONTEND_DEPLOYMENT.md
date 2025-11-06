# FastAPI + React Application Deployment Guide

This guide covers deploying the FastAPI backend and React frontend as two separate Google Cloud Run services alongside the existing Streamlit application.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Google Cloud Run Deployment Architecture               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────┐   ┌────────────────────────┐ │
│  │  sql-rag-frontend    │   │   sql-rag-api          │ │
│  │  (React + Nginx)     │   │   (FastAPI)            │ │
│  │  Port: 8080          │◄──┤   Port: 8080           │ │
│  │  Memory: 512Mi       │   │   Memory: 2Gi          │ │
│  └──────────────────────┘   └────────────────────────┘ │
│           │                           │                 │
│           │                           │                 │
│           └───────────┬───────────────┘                 │
│                       │                                 │
│           ┌───────────▼───────────┐                     │
│           │   sql-rag-app         │                     │
│           │   (Streamlit)         │                     │
│           │   Port: 8080          │                     │
│           └───────────────────────┘                     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Deployment Files

### 1. Backend Configuration

**Dockerfile.api** - FastAPI backend container
- Base: Python 3.11-slim
- Entry point: `uvicorn api.main:app`
- Port: 8080
- Health check: `/health` endpoint

**Key Features:**
- Optimized for Google Cloud Run
- Includes all necessary dependencies from requirements.txt
- Copies FAISS indices and schema files
- Configurable via environment variables

### 2. Frontend Configuration

**Dockerfile.frontend** - React frontend container (multi-stage)
- Build stage: Node.js 20 (npm install + build)
- Production stage: Nginx Alpine
- Port: 8080
- Health check: `/health` endpoint

**frontend/nginx.conf** - Nginx configuration
- SPA routing support (all routes → index.html)
- Gzip compression enabled
- Static asset caching
- Security headers

### 3. Deployment Script

**deploy_api_frontend.sh** - Automated deployment script
- Deploys both backend and frontend
- Configures CORS between services
- Sets up secrets and permissions
- Provides service URLs after deployment

## Prerequisites

1. **Google Cloud CLI** installed and configured
   ```bash
   gcloud --version
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **API Keys** (set as environment variables or will be prompted):
   ```bash
   export OPENAI_API_KEY="sk-your-openai-key"
   export GEMINI_API_KEY="your-gemini-key"
   ```

3. **Billing enabled** on your Google Cloud project

4. **Required APIs** (will be enabled by script):
   - Cloud Build API
   - Cloud Run API
   - Artifact Registry API
   - Secret Manager API
   - Firestore API
   - BigQuery API

## Deployment Steps

### Option 1: Automated Deployment (Recommended)

Run the deployment script from the `rag_app/` directory:

```bash
cd rag_app

# Using current gcloud project
./deploy_api_frontend.sh

# Or specify project explicitly
./deploy_api_frontend.sh --project-id YOUR_PROJECT_ID

# With custom service names
./deploy_api_frontend.sh \
  --project-id YOUR_PROJECT_ID \
  --backend-service my-api \
  --frontend-service my-ui \
  --region us-west1
```

The script will:
1. ✅ Check prerequisites
2. ✅ Enable required Google Cloud APIs
3. ✅ Create Artifact Registry repository
4. ✅ Set up Firestore database
5. ✅ Create/update secrets in Secret Manager
6. ✅ Build and deploy backend (sql-rag-api)
7. ✅ Build and deploy frontend (sql-rag-frontend)
8. ✅ Configure CORS between services
9. ✅ Display service URLs

**Deployment time:** ~10-15 minutes

### Option 2: Manual Deployment

#### Step 1: Build and Deploy Backend

```bash
# Set project
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Build backend image
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/sql-rag-repo/sql-rag-api:latest \
  --dockerfile Dockerfile.api \
  --timeout 20m

# Deploy backend
gcloud run deploy sql-rag-api \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/sql-rag-repo/sql-rag-api:latest \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars "PYTHONUNBUFFERED=1,EMBEDDINGS_PROVIDER=openai,BIGQUERY_PROJECT_ID=${PROJECT_ID}" \
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest"

> **Important:** the value after each `=` in `--set-secrets` is the Secret Manager resource (`<secret-name>:<version>`), not the literal API key. For example `OPENAI_API_KEY=openai-api-key:latest` mounts the secret named `openai-api-key`. Passing `sk-...` or `AIza...` here will make Cloud Run look for a secret with that exact name and the deploy will fail.

# Get backend URL
export BACKEND_URL=$(gcloud run services describe sql-rag-api --region ${REGION} --format='value(status.url)')
echo "Backend URL: $BACKEND_URL"
```

#### Step 2: Build and Deploy Frontend

```bash
# Build frontend image with backend URL
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/sql-rag-repo/sql-rag-frontend:latest \
  --dockerfile Dockerfile.frontend \
  --build-arg "VITE_API_BASE_URL=${BACKEND_URL}" \
  --timeout 20m

# Deploy frontend
gcloud run deploy sql-rag-frontend \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/sql-rag-repo/sql-rag-frontend:latest \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --set-env-vars "VITE_API_BASE_URL=${BACKEND_URL}"

# Get frontend URL
export FRONTEND_URL=$(gcloud run services describe sql-rag-frontend --region ${REGION} --format='value(status.url)')
echo "Frontend URL: $FRONTEND_URL"
```

#### Step 3: Update CORS Configuration

```bash
# Update backend to allow frontend origin
gcloud run services update sql-rag-api \
  --region ${REGION} \
  --update-env-vars "CORS_ORIGINS=${FRONTEND_URL}"
```

## Post-Deployment Verification

### 1. Health Checks

```bash
# Check backend health
curl https://sql-rag-api-xxxxx.run.app/health

# Check frontend health
curl https://sql-rag-frontend-xxxxx.run.app/health

# Check API documentation
open https://sql-rag-api-xxxxx.run.app/docs
```

### 2. Test End-to-End Flow

1. **Open Frontend**: Navigate to frontend URL in browser
2. **Test Query Search**:
   - Go to Chat or SQL Playground tab
   - Enter a query: "Show me total revenue by product category"
   - Verify SQL generation and results
3. **Test Dashboard**: Create a simple visualization
4. **Check CORS**: Ensure no CORS errors in browser console

### 3. Monitor Logs

```bash
# Backend logs
gcloud run services logs tail sql-rag-api --region us-central1

# Frontend logs (nginx access logs)
gcloud run services logs tail sql-rag-frontend --region us-central1
```

## Configuration

### Environment Variables

#### Backend (sql-rag-api)

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | From Secret Manager |
| `OPENAI_API_KEY` | OpenAI API key | From Secret Manager |
| `BIGQUERY_PROJECT_ID` | BigQuery project | Same as deployment project |
| `BIGQUERY_DATASET` | BigQuery dataset | `bigquery-public-data.thelook_ecommerce` |
| `EMBEDDINGS_PROVIDER` | Embedding provider | `openai` |
| `CORS_ORIGINS` | Allowed CORS origins | Frontend URL |
| `PORT` | Service port | `8080` |

#### Frontend (sql-rag-frontend)

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API URL | Set during build |

### Service Resources

**Backend (sql-rag-api):**
- Memory: 2Gi
- CPU: 2
- Max instances: 10
- Timeout: 300s
- Concurrency: 80

**Frontend (sql-rag-frontend):**
- Memory: 512Mi (static serving is lightweight)
- CPU: 1
- Max instances: 5
- Timeout: 60s
- Concurrency: 80

## Troubleshooting

### Issue: CORS Errors

**Symptom**: Browser console shows CORS errors when frontend calls backend

**Solution**:
```bash
# Verify CORS configuration
gcloud run services describe sql-rag-api --region us-central1 --format='value(spec.template.spec.containers[0].env[?name=="CORS_ORIGINS"].value)'

# Update if needed
gcloud run services update sql-rag-api \
  --region us-central1 \
  --update-env-vars "CORS_ORIGINS=https://sql-rag-frontend-xxxxx.run.app"
```

### Issue: Backend Health Check Fails

**Symptom**: `/health` endpoint returns 404 or times out

**Solution**:
```bash
# Check logs
gcloud run services logs read sql-rag-api --region us-central1 --limit 50

# Verify FastAPI is running
gcloud run services describe sql-rag-api --region us-central1 --format='value(status.conditions[0].message)'
```

### Issue: Frontend Shows Blank Page

**Symptom**: Frontend loads but shows blank white page

**Solution**:
1. Check browser console for errors
2. Verify VITE_API_BASE_URL is set correctly:
   ```bash
   gcloud run services describe sql-rag-frontend --region us-central1 --format='value(spec.template.spec.containers[0].env[?name=="VITE_API_BASE_URL"].value)'
   ```
3. Check nginx logs:
   ```bash
   gcloud run services logs read sql-rag-frontend --region us-central1 --limit 50
   ```

### Issue: Build Fails

**Symptom**: Cloud Build times out or fails

**Solution**:
1. Check Cloud Build logs:
   ```bash
   gcloud builds list --limit 5
   gcloud builds log [BUILD_ID]
   ```
2. Increase timeout: Add `--timeout 30m` to gcloud builds submit
3. Check .dockerignore - ensure node_modules excluded

### Issue: Out of Memory

**Symptom**: Backend crashes with OOM errors

**Solution**:
```bash
# Increase memory allocation
gcloud run services update sql-rag-api \
  --region us-central1 \
  --memory 4Gi
```

## Cost Optimization

### Estimated Monthly Costs (Light Usage)

| Service | Memory | Requests/month | Estimated Cost |
|---------|--------|----------------|----------------|
| Backend | 2Gi | 10,000 | ~$5-10 |
| Frontend | 512Mi | 50,000 | ~$2-5 |
| Artifact Registry | - | Storage only | ~$1-2 |
| **Total** | | | **~$8-17/month** |

**Notes:**
- Cloud Run pricing: Pay only for request time
- Min instances = 0 (no idle costs)
- First 2 million requests free per month
- Actual costs depend on usage patterns

### Cost Reduction Tips

1. **Use smaller instances** for development:
   ```bash
   --memory 1Gi --cpu 1
   ```

2. **Enable request concurrency**:
   ```bash
   --concurrency 100
   ```

3. **Set max instances** to prevent runaway costs:
   ```bash
   --max-instances 3
   ```

4. **Use caching** (already implemented in application)

5. **Monitor usage**:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision" --limit 100
   ```

## Updating the Application

### Update Backend Only

```bash
# Make code changes
# Then redeploy
./deploy_api_frontend.sh --project-id YOUR_PROJECT_ID

# Or manually
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/sql-rag-repo/sql-rag-api:latest --dockerfile Dockerfile.api
gcloud run services update sql-rag-api --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/sql-rag-repo/sql-rag-api:latest --region us-central1
```

### Update Frontend Only

```bash
# Make frontend changes in frontend/src/
# Then redeploy
cd frontend
npm run build  # Test build locally first

# Deploy
cd ..
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/sql-rag-repo/sql-rag-frontend:latest --dockerfile Dockerfile.frontend
gcloud run services update sql-rag-frontend --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/sql-rag-repo/sql-rag-frontend:latest --region us-central1
```

## Rollback

```bash
# List revisions
gcloud run revisions list --service sql-rag-api --region us-central1

# Rollback to previous revision
gcloud run services update-traffic sql-rag-api \
  --to-revisions REVISION_NAME=100 \
  --region us-central1
```

## Clean Up

### Delete Individual Services

```bash
# Delete backend
gcloud run services delete sql-rag-api --region us-central1

# Delete frontend
gcloud run services delete sql-rag-frontend --region us-central1
```

### Delete All Resources

```bash
# Delete all Cloud Run services
gcloud run services delete sql-rag-api --region us-central1 --quiet
gcloud run services delete sql-rag-frontend --region us-central1 --quiet
gcloud run services delete sql-rag-app --region us-central1 --quiet

# Delete Artifact Registry images
gcloud artifacts docker images delete \
  ${REGION}-docker.pkg.dev/${PROJECT_ID}/sql-rag-repo/sql-rag-api:latest

gcloud artifacts docker images delete \
  ${REGION}-docker.pkg.dev/${PROJECT_ID}/sql-rag-repo/sql-rag-frontend:latest

# Keep secrets for reuse (or delete if no longer needed)
# gcloud secrets delete openai-api-key
# gcloud secrets delete gemini-api-key
```

## Security Considerations

1. **API Keys**: Stored in Secret Manager (never in code/env files)
2. **CORS**: Restricted to frontend origin in production
3. **Authentication**: Currently allows unauthenticated access (add IAM for production)
4. **SQL Injection**: Protected by SQL validator in backend
5. **BigQuery**: Read-only access enforced

### Production Hardening

For production deployments:

1. **Enable authentication**:
   ```bash
   gcloud run services update sql-rag-api --no-allow-unauthenticated
   gcloud run services add-iam-policy-binding sql-rag-api \
     --member="user:your-email@example.com" \
     --role="roles/run.invoker"
   ```

2. **Use custom domain**:
   ```bash
   gcloud run domain-mappings create --service sql-rag-frontend --domain api.yourdomain.com
   ```

3. **Enable Cloud Armor** for DDoS protection

4. **Set up monitoring and alerting**:
   ```bash
   gcloud monitoring alert-policies create --notification-channels=CHANNEL_ID --display-name="High Error Rate" --condition-display-name="Error rate > 5%"
   ```

## Support

For issues or questions:
- Check logs: `gcloud run services logs tail SERVICE_NAME --region REGION`
- Review Cloud Build logs: `gcloud builds list --limit 5`
- Consult [Cloud Run documentation](https://cloud.google.com/run/docs)

## Next Steps

After successful deployment:
1. ✅ Test all application features
2. ✅ Set up monitoring and alerts
3. ✅ Configure custom domain (optional)
4. ✅ Enable authentication (for production)
5. ✅ Set up CI/CD pipeline (optional)
