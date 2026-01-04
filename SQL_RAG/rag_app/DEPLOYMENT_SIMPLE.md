# Simple Cloud Run Deployment (MVP)

Ultra-simple deployment for your SQL RAG FastAPI application using Google Cloud Run's **buildpack approach** - no Dockerfile needed!

## What's Different from the Complex Approach?

| Feature | Complex (Old) | Simple (MVP) |
|---------|---------------|--------------|
| Dockerfile | ✅ Required | ❌ Not needed |
| Cloud Build YAML | ✅ Required | ❌ Not needed |
| Secret Manager | ✅ Used | ❌ Env vars instead |
| Lines of code | 368 lines | ~50 lines |
| Setup time | 15-20 minutes | 3-5 minutes |
| Production-ready | ✅ Yes | ⚠️ MVP only |

## How It Works

Google Cloud Run's buildpacks automatically:
1. **Detect** your Python application (from `requirements.txt`)
2. **Build** a container image for you
3. **Deploy** to Cloud Run
4. **Start** your app using the `Procfile`

No Docker knowledge needed!

## Prerequisites

1. **Google Cloud CLI** installed:
   ```bash
   gcloud --version
   ```
   If not installed: https://cloud.google.com/sdk/docs/install

2. **Authenticated with Google Cloud**:
   ```bash
   gcloud auth login
   gcloud config set project brainrot-453319
   ```

3. **Billing enabled** on your Google Cloud project

## Quick Start (3 Steps)

### Step 1: Set Up API Keys

Copy the example file and fill in your keys:

```bash
cd rag_app
cp .env.deploy.example .env.deploy
```

Edit `.env.deploy` with your actual keys:
```bash
OPENAI_API_KEY=sk-proj-YOUR_REAL_KEY_HERE
GEMINI_API_KEY=YOUR_REAL_GEMINI_KEY_HERE
```

**Important:** `.env.deploy` is git-ignored and never uploaded to Cloud Run. Keys are passed as environment variables during deployment.

### Step 2: Make Deploy Script Executable

```bash
chmod +x deploy.sh
```

### Step 3: Deploy

```bash
./deploy.sh
```

That's it! ☕ Grab coffee while Cloud Run builds and deploys (3-5 minutes first time).

## What Happens During Deployment

1. **Loads your API keys** from `.env.deploy`
2. **Uploads source code** to Cloud Build (excluding files in `.gcloudignore`)
3. **Buildpacks auto-detect** Python and install dependencies
4. **Creates container** automatically
5. **Deploys to Cloud Run** with your configuration
6. **Returns service URL** - your API is live!

## After Deployment

You'll see output like:
```
Deployment complete!

Service URL:
https://sql-rag-api-xxxxx-uc.a.run.app

API Docs:
https://sql-rag-api-xxxxx-uc.a.run.app/docs
```

Test it:
```bash
# Health check
curl https://sql-rag-api-xxxxx-uc.a.run.app/health

# Open API docs in browser
open https://sql-rag-api-xxxxx-uc.a.run.app/docs
```

## Configuration

### Customize Deployment

You can override defaults in `.env.deploy`:

```bash
# Your API keys (required)
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AIza...

# Optional overrides
PROJECT_ID=your-other-project
REGION=us-west1
SERVICE_NAME=my-custom-name
MEMORY=4Gi
CPU=4
```

### Command Line Overrides

Or pass directly when deploying:
```bash
PROJECT_ID=my-project MEMORY=4Gi ./deploy.sh
```

## Key Files

| File | Purpose |
|------|---------|
| `Procfile` | Tells Cloud Run how to start your app |
| `deploy.sh` | Simple deployment script (~50 lines) |
| `.env.deploy` | Your API keys (git-ignored) |
| `.env.deploy.example` | Template for API keys |
| `.gcloudignore` | Files to exclude from upload |

## Updating Your Application

Made code changes? Just redeploy:

```bash
./deploy.sh
```

Cloud Run will:
- Upload new code
- Rebuild container
- Deploy new version
- Automatically route traffic to new version

## Troubleshooting

### "OPENAI_API_KEY must be set"

**Problem:** API keys not found

**Solution:**
```bash
# Make sure .env.deploy exists and has keys
cat .env.deploy

# Or export them directly
export OPENAI_API_KEY="sk-proj-..."
export GEMINI_API_KEY="AIza..."
./deploy.sh
```

### "gcloud: command not found"

**Problem:** Google Cloud CLI not installed

**Solution:** Install from https://cloud.google.com/sdk/docs/install

### "Permission denied: ./deploy.sh"

**Problem:** Script not executable

**Solution:**
```bash
chmod +x deploy.sh
```

### Deployment Takes Forever

**First deployment:** 5-7 minutes is normal (building from scratch)

**Subsequent deploys:** Should be 3-4 minutes

**If stuck longer:** Check Cloud Build logs:
```bash
gcloud builds list --limit 5
gcloud builds log [BUILD_ID]
```

### "Failed to build: Procfile not found"

**Problem:** Running from wrong directory

**Solution:**
```bash
cd rag_app
./deploy.sh
```

### Build Fails with "Module not found"

**Problem:** Missing dependency in `requirements.txt`

**Solution:** Add the missing package:
```bash
echo "missing-package==1.0.0" >> requirements.txt
./deploy.sh
```

## Monitoring

### View Logs

```bash
# Stream live logs
gcloud run services logs tail sql-rag-api --region us-central1

# View recent logs
gcloud run services logs read sql-rag-api --region us-central1 --limit 100
```

### Service Status

```bash
# Get service details
gcloud run services describe sql-rag-api --region us-central1

# List all services
gcloud run services list
```

## Cost Estimates (MVP Usage)

With minimal traffic (learning/testing):
- **First 2M requests/month:** FREE
- **Memory (2GB):** ~$0.000003 per second
- **CPU (2 vCPU):** ~$0.000024 per second
- **Estimated monthly cost:** $5-15 for light development use

With `min-instances=0` (default), you only pay when requests are being processed.

## Security Considerations (MVP)

⚠️ **This is an MVP deployment** - good for development, not production:

| Aspect | Current (MVP) | Production Recommendation |
|--------|---------------|---------------------------|
| API Keys | Environment variables | Use Secret Manager |
| CORS | `*` (allow all) | Restrict to specific domains |
| Authentication | Unauthenticated | Add IAM or API keys |
| HTTPS | ✅ Automatic | ✅ Keep enabled |

To migrate to production setup later, see `API_FRONTEND_DEPLOYMENT.md`.

## Next Steps

### For Production

When ready to graduate from MVP:

1. **Add Secret Manager:**
   ```bash
   # Create secrets
   echo "sk-proj-..." | gcloud secrets create openai-api-key --data-file=-

   # Update deployment to use secrets
   --set-secrets "OPENAI_API_KEY=openai-api-key:latest"
   ```

2. **Add authentication:**
   ```bash
   gcloud run services update sql-rag-api --no-allow-unauthenticated
   ```

3. **Restrict CORS:**
   Update `CORS_ORIGINS` to your frontend domain

4. **Add monitoring:**
   Set up alerts in Cloud Monitoring

5. **Use the full deployment script:**
   See `deploy_api_frontend.sh` for production approach

### Deploy Frontend

Want to deploy the React frontend too?

```bash
# Coming soon: deploy_frontend.sh
# For now, use the full script: ./deploy_api_frontend.sh
```

## Comparison with Complex Approach

When should you upgrade from this simple approach?

**Stick with simple if:**
- ✅ Building an MVP/prototype
- ✅ Solo developer or small team
- ✅ Low traffic (< 10k requests/month)
- ✅ Not handling sensitive user data

**Upgrade to complex if:**
- ❌ Going to production
- ❌ Multiple services (frontend + backend)
- ❌ Need Secret Manager for compliance
- ❌ Need sophisticated CI/CD
- ❌ Multiple environments (dev/staging/prod)

## Support

### Get Help

```bash
# Check deployment status
gcloud run services describe sql-rag-api --region us-central1

# View recent errors
gcloud run services logs read sql-rag-api --region us-central1 --limit 50

# See what's being uploaded
cat .gcloudignore
```

### Useful Commands

```bash
# Delete service
gcloud run services delete sql-rag-api --region us-central1

# Update single env var
gcloud run services update sql-rag-api \
  --update-env-vars "NEW_VAR=value" \
  --region us-central1

# View all env vars
gcloud run services describe sql-rag-api \
  --region us-central1 \
  --format='value(spec.template.spec.containers[0].env)'
```

## Files You Can Delete (If Using Simple Approach)

Once you confirm the simple deployment works:

```bash
# Optional: Remove complex deployment files
rm Dockerfile.api
rm Dockerfile.frontend
rm cloudbuild.api.yaml
rm cloudbuild.frontend.yaml
rm deploy_api_frontend.sh

# Keep these
# - Procfile (required)
# - deploy.sh (required)
# - .env.deploy (required, git-ignored)
# - .gcloudignore (required)
```

---

**Questions?** Check Cloud Run docs: https://cloud.google.com/run/docs/quickstarts/build-and-deploy

**Ready to deploy?** `./deploy.sh` 🚀
