# Frontend Deployment Troubleshooting Guide

**Date:** December 17, 2025
**Issue:** "Failed to fetch" error on React frontend
**Services Affected:**
- Frontend: `sql-rag-frontend-simple` (https://sql-rag-frontend-simple-orvqbubh7q-uc.a.run.app)
- Backend: `sql-rag-api-simple` (https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app)

---

## Executive Summary

### Initial Problem
User reported that the React frontend loaded successfully but displayed a "failed to fetch" error when attempting to submit queries. The backend API appeared to be deployed and running.

### Root Causes Discovered
1. **Backend Issue:** FAISS vector embedding dimension mismatch (OpenAI 1536D vs Gemini 768D)
2. **Frontend Issue:** Cloud Run buildpack deployment limitation preventing build-time environment variables from being set
3. **Result:** Frontend JavaScript compiled with `http://localhost:8080` instead of production backend URL

### Final Solution
Switch from Cloud Run buildpack deployment to Dockerfile-based deployment with build arguments to properly inject `VITE_API_BASE_URL` during the Vite build process.

---

## Timeline of Investigation

### Phase 1: Initial Error Report
**User Report:** "Failed to fetch" error on frontend URL
**Initial Hypothesis:** API key issues or backend service down

### Phase 2: Backend Embedding Mismatch (RESOLVED)
**Discovery:** Backend configured with `EMBEDDINGS_PROVIDER=openai` but FAISS index built with Gemini embeddings
**Error:** `AssertionError` in FAISS dimension check (768 != 1536)
**Fix Applied:** Changed `deploy_api_simple.sh` line 165 from `openai` to `gemini`
**Result:** Backend API now working correctly ✅

### Phase 3: Stale Frontend Build (PARTIAL)
**Discovery:** Frontend last deployed Nov 20, 2025; backend fixed Dec 17, 2025
**Hypothesis:** Frontend has outdated build with old configuration
**Action Taken:** Redeployed frontend using `./deploy_frontend_simple.sh`
**Result:** Deployment succeeded but error persisted ❌

### Phase 4: Network Tab Analysis (CRITICAL)
**Discovery:** Browser Network tab showed:
- Red/cancelled requests labeled "quick" and "search"
- Warning: "⚠️ Provisional headers are shown"
- Request URL: `http://localhost:8080/...` (not production URL!)

**Interpretation:**
- "Provisional headers" means request was cancelled before leaving the browser
- Browser tried to connect to `localhost:8080` which doesn't exist in production
- This indicates the JavaScript bundle has `localhost:8080` hardcoded

### Phase 5: Root Cause - Buildpack Limitation (IDENTIFIED)
**Discovery:** Cloud Run buildpacks don't support build-time environment variables
**Technical Issue:** `--set-env-vars` only sets runtime env vars, but Vite needs `VITE_API_BASE_URL` during build
**Result:** Frontend compiled with fallback value `http://localhost:8080`

---

## Files Read and Analyzed

### Backend Files
1. **`/Users/kanumadhok/Downloads/code/Sql_Rag_Demo/SQL_RAG/rag_app/deploy_api_simple.sh`**
   - Lines 165: `EMBEDDINGS_PROVIDER` configuration
   - Lines 27-31: API key validation
   - Lines 155-166: `gcloud run deploy` command with env vars

2. **`/Users/kanumadhok/Downloads/code/Sql_Rag_Demo/SQL_RAG/rag_app/api/main.py`** (via agent)
   - CORS configuration
   - Endpoint definitions
   - Vector store initialization

3. **Backend Cloud Run logs** (via `gcloud` commands)
   - FAISS AssertionError: `assert d == self.d`
   - Embedding dimension mismatch evidence

### Frontend Files
4. **`/Users/kanumadhok/Downloads/code/Sql_Rag_Demo/SQL_RAG/rag_app/deploy_frontend_simple.sh`**
   - Backend URL detection logic
   - `gcloud run deploy` with `--set-env-vars "VITE_API_BASE_URL=$BACKEND_URL"`
   - Buildpack deployment approach

5. **`/Users/kanumadhok/Downloads/code/Sql_Rag_Demo/SQL_RAG/rag_app/frontend/src/services/ragClient.js`** (via agent)
   - Line 3: `const rawBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080"`
   - API client configuration
   - Fallback to localhost when VITE_API_BASE_URL is undefined

6. **`/Users/kanumadhok/Downloads/code/Sql_Rag_Demo/SQL_RAG/rag_app/frontend/.dockerignore`** (via agent)
   - Line 17-22: `.env` files excluded from Docker context
   - Confirms environment variables must come from deployment, not local files

7. **`/Users/kanumadhok/Downloads/code/Sql_Rag_Demo/SQL_RAG/rag_app/frontend/.env`** (via agent)
   - Contains: `VITE_API_BASE_URL=http://localhost:8080`
   - This is the fallback value being used when env var not set during build

8. **`/Users/kanumadhok/Downloads/code/Sql_Rag_Demo/SQL_RAG/rag_app/frontend/Procfile`** (via agent)
   - `web: npx serve -s dist -l $PORT`
   - Serves pre-built static files from `dist/` directory
   - No runtime environment variable processing possible

9. **`/Users/kanumadhok/Downloads/code/Sql_Rag_Demo/SQL_RAG/rag_app/frontend/package.json`** (via agent)
   - Build script: `"build": "vite build"`
   - Dependencies: React, Vite, Axios
   - Production build creates static files in `dist/`

### Cloud Run Service Metadata
10. **Service deployment history** (via `gcloud run services describe`)
    - Frontend revision: `sql-rag-frontend-simple-00006-9vv` (Dec 17, 2025)
    - Backend revision: `sql-rag-api-simple-00016-9nl` (Dec 17, 2025)
    - Deployment timestamps and configuration

---

## Detailed Error Interactions

### Error 1: Backend FAISS Dimension Mismatch
**When:** Initial backend API calls
**Symptoms:**
- Frontend shows "failed to fetch"
- Backend returns HTTP 500 Internal Server Error

**Backend Logs:**
```python
File "/layers/google.python.pip/pip/lib/python3.13/site-packages/faiss/class_wrappers.py", line 383, in replacement_search
    assert d == self.d
AssertionError
```

**Root Cause:**
- FAISS index built with Gemini embeddings (768 dimensions)
- Backend runtime using OpenAI embeddings (1536 dimensions)
- Query embedding dimension didn't match index dimension

**Fix:**
```bash
# deploy_api_simple.sh line 165 (BEFORE)
--set-env-vars "...EMBEDDINGS_PROVIDER=openai..."

# deploy_api_simple.sh line 165 (AFTER)
--set-env-vars "...EMBEDDINGS_PROVIDER=gemini..."
```

**Verification:**
```bash
curl -s -X POST 'https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app/query/search' \
  -H 'Content-Type: application/json' \
  -d '{"question": "What are the top 5 products by revenue?", "top_k": 3}' | python3 -m json.tool

# Result: ✅ Returns SQL and 20 relevant sources
```

### Error 2: Frontend Still Shows "Failed to Fetch" After Backend Fix
**When:** After backend was fixed and working
**Symptoms:**
- curl tests to backend API succeed
- Browser frontend still shows "failed to fetch"
- No network requests visible in Network tab initially

**Hypothesis:**
Frontend has stale build from before backend was fixed (Nov 20 vs Dec 17)

**Action Taken:**
Redeployed frontend using buildpacks

**Result:**
Deployment succeeded, created revision `sql-rag-frontend-simple-00006-9vv`, but error persisted

### Error 3: Provisional Headers Shown (CRITICAL DISCOVERY)
**When:** User checked Browser DevTools Network tab
**User Report:**
> "In the network page it shows x quit in the name section"

**Network Tab Analysis:**
- **Request Name:** `quick`, `search` (shown in red)
- **Status:** Cancelled/Failed
- **Warning:** "⚠️ Provisional headers are shown"
- **Request URL:** `http://localhost:8080/query/search`

**What "Provisional Headers" Means:**
This browser warning indicates the request was **intercepted or failed before the browser could send it**. The browser never received a response from the server, so it only shows the headers it *intended* to send ("provisional" headers).

**Common Causes:**
1. Request cancelled by JavaScript code
2. Connection refused (server doesn't exist)
3. CORS preflight failure (but this would show OPTIONS request)
4. Mixed content blocking (HTTPS page calling HTTP)

**In This Case:**
The browser tried to connect to `http://localhost:8080`, which doesn't exist in the production environment. The connection immediately fails, resulting in cancelled requests with provisional headers.

### Error 4: Frontend Calling localhost Instead of Production URL
**When:** After examining Network tab request URL
**Discovery:** Frontend JavaScript attempting to call `http://localhost:8080/query/search`

**User Report via Gemini Screenshot Analysis:**
> "Shows a red POST/GET request... When you click on quick, the Headers tab displays the specific warning: ⚠️ Provisional headers are shown"

**Question Asked:** "What URL is the red 'quick' or 'search' request trying to call?"
**User Answer:** "http://localhost:8080/..."

**Implication:**
The frontend's compiled JavaScript has `http://localhost:8080` hardcoded, meaning `VITE_API_BASE_URL` was **undefined during the Vite build process**.

---

## Root Cause Analysis

### Why Vite Needs Build-Time Environment Variables

**Vite's Compilation Process:**
1. During `vite build`, Vite processes all source files
2. Any reference to `import.meta.env.VITE_*` is **replaced with the literal value** at compile time
3. The result is static JavaScript with hardcoded values in the `dist/` folder
4. At runtime, changing environment variables has **no effect** on already-compiled code

**Code Example from `ragClient.js:3`:**
```javascript
// Source code
const rawBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";

// Compiled output when VITE_API_BASE_URL is undefined during build
const rawBase = undefined || "http://localhost:8080";
// Simplifies to:
const rawBase = "http://localhost:8080";

// Compiled output when VITE_API_BASE_URL="https://api.example.com" during build
const rawBase = "https://api.example.com" || "http://localhost:8080";
// Simplifies to:
const rawBase = "https://api.example.com";
```

### Cloud Run Buildpack Limitation

**How Cloud Run Buildpacks Work:**
```
1. Upload source code to Cloud Build
2. Buildpack detects Node.js project
3. Buildpack runs: npm install
4. Buildpack runs: npm run build  ← VITE_API_BASE_URL must be available HERE
5. Container image created with dist/ folder
6. Container deployed to Cloud Run
7. Runtime environment variables set  ← Too late! JavaScript already compiled
```

**The Problem with `--set-env-vars`:**
```bash
gcloud run deploy frontend \
  --source . \
  --set-env-vars "VITE_API_BASE_URL=https://api.example.com"
#                 ↑
#                 This only affects RUNTIME (step 7)
#                 NOT available during BUILD (step 4)
```

**Why This Happens:**
- `gcloud run deploy --source` uses Cloud Build with automatic buildpack detection
- Buildpacks execute build commands in a separate build environment
- `--set-env-vars` configures the **container runtime**, not the build environment
- Google Cloud Run does not provide a `--build-env` flag for source deployments
- This is a **fundamental architectural limitation**, not a bug

**Documentation Evidence:**
From Google Cloud Run documentation:
> "Environment variables set with --set-env-vars are available only at runtime, not during the build process."

### Current Frontend Deployment Flow (BROKEN)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. deploy_frontend_simple.sh detects backend URL           │
│    BACKEND_URL=https://sql-rag-api-simple-...run.app       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. gcloud run deploy --source . \                          │
│    --set-env-vars "VITE_API_BASE_URL=$BACKEND_URL"         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Cloud Build: Buildpack runs "npm install"               │
│    Environment: VITE_API_BASE_URL is NOT SET               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Cloud Build: Buildpack runs "npm run build"             │
│    → vite build                                             │
│    → Reads: import.meta.env.VITE_API_BASE_URL              │
│    → Value: undefined                                       │
│    → Falls back to: "http://localhost:8080"                 │
│    → Compiles into dist/assets/index-abc123.js              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Container image created with dist/ folder               │
│    JavaScript hardcoded with localhost:8080                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Container deployed to Cloud Run                         │
│    VITE_API_BASE_URL env var set at runtime                │
│    ❌ BUT: Has no effect on compiled JavaScript             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Browser loads JavaScript from dist/                     │
│    JavaScript calls: http://localhost:8080                  │
│    Browser shows: "failed to fetch"                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Why Buildpacks Don't Work for Vite

### Technical Explanation

**Buildpacks Are Designed For Runtime Configuration**

Most backend applications (Node.js Express, Python Flask, Java Spring) read environment variables **at runtime**:

```javascript
// Backend Express app - reads at runtime ✅
const PORT = process.env.PORT || 3000;
app.listen(PORT);
```

When the container starts, `process.env.PORT` is evaluated, so runtime env vars work perfectly.

**But Vite Is Different - Build-Time Configuration**

Vite is a **build tool** that creates static files. It reads environment variables **once during build** and bakes them into the JavaScript:

```javascript
// Frontend Vite app - reads at BUILD time ❌ with buildpacks
const API_URL = import.meta.env.VITE_API_BASE_URL;

// After vite build, this becomes literal JavaScript:
const API_URL = "http://localhost:8080"; // Hardcoded!
```

**The Mismatch:**
- Buildpacks set env vars for container **runtime**
- Vite needs env vars during **build time**
- These are two different phases in Cloud Run deployment

### Why This Wasn't Caught Earlier

1. **Local Development Works:**
   - Developers run `npm run dev` with local `.env` file
   - Vite's dev server reads `.env` at startup
   - Everything works fine locally

2. **Buildpack Deployment Appears to Succeed:**
   - No build errors or warnings
   - Container deploys successfully
   - Health checks pass (static file server is running)

3. **Error Only Appears in Browser:**
   - JavaScript compiled with localhost
   - Browser can't connect to localhost in production
   - "Failed to fetch" error

### Industry Standard Solution: Dockerfiles

**Why Dockerfiles Are the Standard for Frontend Apps:**

1. **Build Args Support:**
   ```dockerfile
   ARG VITE_API_BASE_URL
   ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
   RUN npm run build  # Env var available during build
   ```

2. **Explicit Control:**
   - Developer controls exactly when env vars are set
   - Clear separation of build vs runtime configuration
   - Reproducible builds

3. **Multi-Stage Builds:**
   - Build stage with all dependencies
   - Production stage with only runtime needs
   - Smaller final image

4. **Standard Practice:**
   - All major frontend frameworks (React, Vue, Angular) recommend Dockerfile for production
   - CI/CD tools (GitHub Actions, GitLab CI) use Dockerfiles
   - Kubernetes, Cloud Run, AWS ECS all have first-class Dockerfile support

---

## Solutions Comparison

### Solution 1: Dockerfile with Build Args (RECOMMENDED)

**Approach:** Replace buildpack deployment with custom Dockerfile

**Pros:**
- ✅ Full control over build-time vs runtime environment variables
- ✅ Industry standard approach for frontend deployments
- ✅ Explicit and debuggable build process
- ✅ Multi-stage builds for smaller production images
- ✅ Works consistently across all cloud providers
- ✅ Better caching and faster rebuilds

**Cons:**
- Requires creating and maintaining a Dockerfile
- Slightly more complex than "just push code"

**Implementation:**

```dockerfile
# frontend/Dockerfile
# Build stage - includes dev dependencies and source code
FROM node:20-slim AS build

WORKDIR /app

# Copy package files first (better caching)
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build argument for API URL (passed during docker build)
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Build the app - VITE_API_BASE_URL is available here
RUN npm run build

# Production stage - minimal image with only built files
FROM node:20-slim

WORKDIR /app

# Install serve for hosting static files
RUN npm install -g serve

# Copy built assets from build stage
COPY --from=build /app/dist ./dist

EXPOSE 8080

# Serve the static files
CMD ["serve", "-s", "dist", "-l", "8080"]
```

**Updated deployment script:**

```bash
# deploy_frontend_simple.sh

# Auto-detect backend URL
BACKEND_URL=$(gcloud run services describe sql-rag-api-simple \
  --region us-central1 --format='value(status.url)')

# Build container image with build arg
gcloud builds submit \
  --tag "us-central1-docker.pkg.dev/$PROJECT_ID/sql-rag-repo/sql-rag-frontend-simple" \
  --build-arg VITE_API_BASE_URL="$BACKEND_URL" \
  frontend/

# Deploy the built image
gcloud run deploy sql-rag-frontend-simple \
  --image "us-central1-docker.pkg.dev/$PROJECT_ID/sql-rag-repo/sql-rag-frontend-simple" \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 5
```

**Why This Works:**
1. `--build-arg VITE_API_BASE_URL="$BACKEND_URL"` passes variable to Docker build
2. `ARG VITE_API_BASE_URL` in Dockerfile receives the build arg
3. `ENV VITE_API_BASE_URL=$VITE_API_BASE_URL` sets it as environment variable
4. `RUN npm run build` executes with VITE_API_BASE_URL available
5. Vite compiles JavaScript with production URL instead of localhost

### Solution 2: Build Locally, Push Image

**Approach:** Build Docker image on local machine, push to registry, deploy

**Pros:**
- ✅ Guaranteed to work (full control over build environment)
- ✅ Can test build locally before deploying
- ✅ No Cloud Build quota/billing concerns

**Cons:**
- ❌ Slower (build happens on local machine)
- ❌ Requires Docker installed locally
- ❌ Requires local machine to have good internet connection
- ❌ Not suitable for CI/CD pipelines

**Implementation:**

```bash
cd frontend

# Build locally with build arg
docker build \
  --build-arg VITE_API_BASE_URL="https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app" \
  -t "us-central1-docker.pkg.dev/brainrot-453319/sql-rag-repo/sql-rag-frontend-simple" \
  .

# Push to Artifact Registry
docker push "us-central1-docker.pkg.dev/brainrot-453319/sql-rag-repo/sql-rag-frontend-simple"

# Deploy
gcloud run deploy sql-rag-frontend-simple \
  --image "us-central1-docker.pkg.dev/brainrot-453319/sql-rag-repo/sql-rag-frontend-simple" \
  --region us-central1
```

### Solution 3: Cloud Build with pack CLI

**Approach:** Use Cloud Build with explicit buildpack configuration

**Pros:**
- ✅ Uses buildpacks (familiar approach)
- ✅ More control than automatic buildpack detection

**Cons:**
- ❌ More complex than Dockerfile
- ❌ Still requires workarounds for build-time env vars
- ❌ Less standard than Dockerfile approach
- ❌ Harder to debug

**Not Recommended** - adds complexity without clear benefits over Dockerfile

### Solution 4: Runtime Environment Injection (NOT VIABLE)

**Approach:** Inject environment variables at runtime using server-side template

**Concept:**
```javascript
// index.html served by custom server
<script>
  window.__ENV__ = {
    API_BASE_URL: "<%= process.env.VITE_API_BASE_URL %>"
  };
</script>

// ragClient.js
const API_URL = window.__ENV__.API_BASE_URL;
```

**Why This Doesn't Work:**
- ❌ Requires custom server instead of static file serving
- ❌ Breaks Vite's build optimization and tree-shaking
- ❌ Breaks service workers and offline capability
- ❌ Adds unnecessary complexity
- ❌ Goes against frontend best practices

**Not Recommended** - violates principles of static site hosting

---

## Recommended Solution: Dockerfile Implementation

### Step-by-Step Implementation Guide

#### Step 1: Create Dockerfile

Create `/Users/kanumadhok/Downloads/code/Sql_Rag_Demo/SQL_RAG/rag_app/frontend/Dockerfile`:

```dockerfile
# Multi-stage build for optimized production image

# ============================================
# Build Stage - Compile the frontend
# ============================================
FROM node:20-slim AS build

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install all dependencies (including devDependencies for build)
RUN npm ci

# Copy source code
COPY . .

# Accept build argument for API URL
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Verify environment variable is set
RUN echo "Building with VITE_API_BASE_URL=$VITE_API_BASE_URL"

# Build the application
# This creates optimized static files in dist/
RUN npm run build

# List built files for verification
RUN ls -la dist/

# ============================================
# Production Stage - Serve the frontend
# ============================================
FROM node:20-slim

WORKDIR /app

# Install serve globally for hosting static files
RUN npm install -g serve@14.2.1

# Copy only the built assets from build stage
COPY --from=build /app/dist ./dist

# Expose port 8080 (Cloud Run standard)
EXPOSE 8080

# Health check endpoint (serve automatically provides this)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:8080', (r) => {if(r.statusCode !== 200) throw new Error(r.statusCode)})"

# Serve the static files
# -s: Single-page application mode (redirects to index.html)
# -l: Listen port
CMD ["serve", "-s", "dist", "-l", "8080"]
```

#### Step 2: Update Deployment Script

Update `/Users/kanumadhok/Downloads/code/Sql_Rag_Demo/SQL_RAG/rag_app/deploy_frontend_simple.sh`:

```bash
#!/bin/bash
# React Frontend Deployment - Dockerfile with Build Args
# Properly sets VITE_API_BASE_URL during build

set -e

echo "🚀 React Frontend - Dockerfile Deployment"
echo "=========================================="
echo

# Configuration
PROJECT_ID="${PROJECT_ID:-brainrot-453319}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="sql-rag-frontend-simple"
BACKEND_SERVICE="sql-rag-api-simple"
MEMORY="${MEMORY:-512Mi}"
CPU="${CPU:-1}"

# Get backend URL
echo "Detecting backend URL from $BACKEND_SERVICE service..."
BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --format='value(status.url)' 2>/dev/null)

if [ -z "$BACKEND_URL" ]; then
  echo "❌ Error: Could not detect backend URL"
  echo "   Make sure $BACKEND_SERVICE is deployed in $REGION"
  exit 1
fi

echo "✅ Backend URL: $BACKEND_URL"
echo

# Build and deploy with Cloud Build
echo "Building container with VITE_API_BASE_URL=$BACKEND_URL"
echo

gcloud builds submit \
  --tag "us-central1-docker.pkg.dev/$PROJECT_ID/sql-rag-repo/$SERVICE_NAME" \
  --build-arg VITE_API_BASE_URL="$BACKEND_URL" \
  --project "$PROJECT_ID" \
  frontend/

# Deploy to Cloud Run
echo
echo "Deploying to Cloud Run..."
echo

gcloud run deploy "$SERVICE_NAME" \
  --image "us-central1-docker.pkg.dev/$PROJECT_ID/sql-rag-repo/$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory "$MEMORY" \
  --cpu "$CPU" \
  --max-instances 5 \
  --min-instances 0 \
  --timeout 60

echo
echo "✅ Deployment complete!"
echo
echo "Service URL:"
gcloud run services describe "$SERVICE_NAME" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --format='value(status.url)'
echo
```

#### Step 3: Create .dockerignore (if not exists)

Create `/Users/kanumadhok/Downloads/code/Sql_Rag_Demo/SQL_RAG/rag_app/frontend/.dockerignore`:

```
# Dependencies
node_modules/
npm-debug.log
yarn-debug.log
yarn-error.log

# Build output (will be created during docker build)
dist/
build/

# Development files
.env.local
.env.development.local
.env.test.local
.env.production.local

# Version control
.git/
.gitignore

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Testing
coverage/
.nyc_output/
```

#### Step 4: Verify Vite Configuration

Check `/Users/kanumadhok/Downloads/code/Sql_Rag_Demo/SQL_RAG/rag_app/frontend/vite.config.js`:

```javascript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    open: true,
  },
  build: {
    outDir: "dist",
    sourcemap: false, // Set to true for debugging
  },
  // Vite automatically reads import.meta.env.VITE_* from process.env
  // No additional configuration needed
});
```

#### Step 5: Deploy

```bash
cd /Users/kanumadhok/Downloads/code/Sql_Rag_Demo/SQL_RAG/rag_app
./deploy_frontend_simple.sh
```

Expected output:
```
🚀 React Frontend - Dockerfile Deployment
==========================================

Detecting backend URL from sql-rag-api-simple service...
✅ Backend URL: https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app

Building container with VITE_API_BASE_URL=https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app

Creating temporary tarball archive of 42 file(s) totalling 2.1 MiB before compression.
Uploading tarball of [frontend] to [gs://...]...
...
Building with VITE_API_BASE_URL=https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app
...
✅ Deployment complete!
```

#### Step 6: Verify

1. **Check Cloud Build Logs:**
   ```bash
   gcloud builds list --limit=1 --region=us-central1
   # Look for "Building with VITE_API_BASE_URL=https://..." in logs
   ```

2. **Check Deployed Frontend:**
   - Open: https://sql-rag-frontend-simple-orvqbubh7q-uc.a.run.app
   - Open Browser DevTools → Network tab
   - Submit a test query
   - Verify: Request URL shows `https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app` (NOT localhost)
   - Verify: HTTP 200 responses
   - Verify: No "failed to fetch" error

3. **Check Compiled JavaScript:**
   ```bash
   # Download the compiled JavaScript bundle
   curl -s https://sql-rag-frontend-simple-orvqbubh7q-uc.a.run.app | grep -o 'src="[^"]*\.js"' | head -1
   # Then inspect that JS file for the API URL
   ```

---

## Verification Steps

### After Successful Deployment

#### 1. Browser Network Tab Check

**Steps:**
1. Open https://sql-rag-frontend-simple-orvqbubh7q-uc.a.run.app
2. Press F12 to open DevTools
3. Go to Network tab
4. Clear any existing requests (trash can icon)
5. Submit a test query: "What are the top products by revenue?"

**Expected Results:**
✅ Request Name: `search` or `quick` (shows in **black**, not red)
✅ Status: `200` (not cancelled or failed)
✅ Request URL: `https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app/query/search`
✅ Response: JSON with `sql`, `answer`, `sources` fields
✅ No "provisional headers" warning

**Red Flags:**
❌ Red/cancelled requests
❌ "Provisional headers are shown" warning
❌ Request URL contains `localhost:8080`
❌ CORS errors
❌ HTTP 500 errors

#### 2. Browser Console Tab Check

**Steps:**
1. In DevTools, go to Console tab
2. Look for any red error messages

**Expected Results:**
✅ No errors
✅ May see informational logs

**Red Flags:**
❌ `net::ERR_FAILED`
❌ CORS policy errors
❌ Failed to fetch
❌ Network errors

#### 3. Response Verification

**Steps:**
1. In Network tab, click on the successful `search` request
2. Go to Response tab

**Expected Results:**
✅ Valid JSON response
✅ Contains `sql` field with BigQuery SQL
✅ Contains `sources` array with relevant examples
✅ Contains `answer` field with formatted SQL

#### 4. Backend Logs Check

**Steps:**
```bash
gcloud run services logs read sql-rag-api-simple \
  --region us-central1 \
  --limit 50
```

**Expected Results:**
✅ No FAISS dimension errors
✅ No 500 Internal Server Error entries
✅ Shows successful query processing

---

## Future Recommendations

### 1. Deployment Best Practices

**Version Tagging:**
```bash
# Tag images with version instead of latest
VERSION="v1.0.0"
gcloud builds submit \
  --tag "us-central1-docker.pkg.dev/$PROJECT_ID/sql-rag-repo/frontend:$VERSION"
```

**Environment-Specific Deployments:**
```bash
# Development
deploy_frontend_simple.sh --env=dev --backend=sql-rag-api-dev

# Production
deploy_frontend_simple.sh --env=prod --backend=sql-rag-api-prod
```

**Automated Testing in CI/CD:**
```yaml
# .github/workflows/deploy-frontend.yml
- name: Build and test
  run: |
    docker build --build-arg VITE_API_BASE_URL=${{ secrets.API_URL }} .
    docker run --rm image npm test
```

### 2. Monitoring and Debugging

**Add Health Check Endpoint:**
```javascript
// frontend/src/config.js
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL,
  version: import.meta.env.VITE_VERSION,
  buildTime: import.meta.env.VITE_BUILD_TIME,
};

// frontend/public/health.json (generated during build)
{
  "status": "ok",
  "version": "1.0.0",
  "apiUrl": "https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app",
  "buildTime": "2025-12-17T04:08:00Z"
}
```

**Add Version Display in UI:**
```javascript
// Show build info in footer or console
console.log('Frontend version:', config.version);
console.log('API URL:', config.apiBaseUrl);
console.log('Build time:', config.buildTime);
```

**Cloud Run Logging:**
```bash
# Set up log-based metrics
gcloud logging metrics create frontend_errors \
  --description="Frontend error requests" \
  --log-filter='resource.type="cloud_run_revision"
    resource.labels.service_name="sql-rag-frontend-simple"
    severity>=ERROR'
```

### 3. Architecture Improvements

**API Gateway Pattern:**
Instead of frontend directly calling backend, use an API Gateway:
```
Frontend → API Gateway → Backend Services
```

Benefits:
- Single origin for CORS (no CORS issues)
- Request routing and load balancing
- Authentication/authorization layer
- Rate limiting and caching

**Configuration Service:**
Create a `/config` endpoint that frontend calls at runtime:
```javascript
// Backend /config endpoint
app.get('/config', (req, res) => {
  res.json({
    apiVersion: '1.0.0',
    features: { advancedSearch: true },
    limits: { maxQueryLength: 1000 }
  });
});
```

This allows some runtime configuration without rebuilding frontend.

### 4. Documentation

**Create DEPLOYMENT.md:**
Document the complete deployment process:
- Prerequisites (gcloud, Docker, npm)
- Environment variables needed
- Step-by-step deployment
- Troubleshooting guide
- Rollback procedures

**Create ARCHITECTURE.md:**
Document the system architecture:
- Frontend (React + Vite)
- Backend (FastAPI)
- Vector Store (FAISS)
- Database (BigQuery)
- LLM (Gemini)

### 5. Testing Strategy

**Pre-Deployment Checks:**
```bash
# Verify backend is healthy
curl https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app/health

# Build locally first
cd frontend
docker build --build-arg VITE_API_BASE_URL=$BACKEND_URL .

# Test the built image
docker run -p 8080:8080 image-name
curl http://localhost:8080  # Should serve React app
```

**Automated E2E Tests:**
```javascript
// tests/e2e/frontend.spec.js
describe('Frontend Integration', () => {
  it('should call correct backend URL', async () => {
    const response = await page.evaluate(() => {
      return fetch('/query/search', {
        method: 'POST',
        body: JSON.stringify({ question: 'test' })
      }).then(r => r.url);
    });
    expect(response).toContain('sql-rag-api-simple');
    expect(response).not.toContain('localhost');
  });
});
```

---

## Appendix A: Command Reference

### Useful Commands for Debugging

**Check Cloud Run Service Status:**
```bash
gcloud run services describe sql-rag-frontend-simple \
  --region us-central1 \
  --format=yaml
```

**View Recent Cloud Build Logs:**
```bash
gcloud builds list --region=us-central1 --limit=5

BUILD_ID="..." # Get from above
gcloud builds log $BUILD_ID --region=us-central1
```

**View Cloud Run Logs:**
```bash
gcloud run services logs read sql-rag-frontend-simple \
  --region us-central1 \
  --limit 100
```

**Test Backend API Directly:**
```bash
curl -X POST 'https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app/query/search' \
  -H 'Content-Type: application/json' \
  -H 'Origin: https://sql-rag-frontend-simple-orvqbubh7q-uc.a.run.app' \
  -d '{"question": "Show me top products", "top_k": 3}'
```

**Check CORS Configuration:**
```bash
curl -I -X OPTIONS 'https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app/query/search' \
  -H 'Origin: https://sql-rag-frontend-simple-orvqbubh7q-uc.a.run.app' \
  -H 'Access-Control-Request-Method: POST'
```

**Inspect Docker Image:**
```bash
# Pull the deployed image
docker pull us-central1-docker.pkg.dev/brainrot-453319/sql-rag-repo/sql-rag-frontend-simple

# Inspect it
docker run --rm -it \
  us-central1-docker.pkg.dev/brainrot-453319/sql-rag-repo/sql-rag-frontend-simple \
  sh

# Inside container:
ls -la dist/
cat dist/index.html
# Check if JavaScript contains localhost or production URL
```

---

## Appendix B: Related Issues and Solutions

### Issue: CORS Errors After Deployment

**Symptoms:**
- Backend returns HTTP 200
- Browser shows CORS error in console
- Network tab shows failed preflight request (OPTIONS)

**Solution:**
Update backend CORS configuration:
```bash
gcloud run services update sql-rag-api-simple \
  --update-env-vars "CORS_ORIGINS=https://sql-rag-frontend-simple-orvqbubh7q-uc.a.run.app"
```

Or use wildcard for development (NOT recommended for production):
```bash
--update-env-vars "CORS_ORIGINS=*"
```

### Issue: Mixed Content Warning

**Symptoms:**
- Frontend served over HTTPS
- Trying to call HTTP API
- Browser blocks request

**Solution:**
Ensure backend URL uses HTTPS in VITE_API_BASE_URL:
```bash
# Wrong
VITE_API_BASE_URL=http://sql-rag-api-simple-orvqbubh7q-uc.a.run.app

# Correct
VITE_API_BASE_URL=https://sql-rag-api-simple-orvqbubh7q-uc.a.run.app
```

### Issue: Build Fails with "Cannot find module"

**Symptoms:**
- Docker build fails
- Error: `Cannot find module 'vite'`

**Solution:**
Ensure package.json and package-lock.json are copied before npm ci:
```dockerfile
COPY package*.json ./
RUN npm ci
# Then copy source code
COPY . .
```

### Issue: Frontend Shows Cached Old Version

**Symptoms:**
- Deployed new version
- Browser still shows old frontend
- Network tab shows 304 Not Modified

**Solution:**
Hard refresh browser:
- Chrome/Firefox: Ctrl+Shift+R (Cmd+Shift+R on Mac)
- Or open DevTools → Network → Disable cache checkbox

Server-side: Add cache-control headers:
```javascript
// serve configuration
serve -s dist --single --no-cache
```

---

## Conclusion

This troubleshooting guide documents the complete journey from initial "failed to fetch" error to the root cause (Cloud Run buildpack limitation with Vite build-time environment variables) to the recommended solution (Dockerfile-based deployment).

**Key Takeaways:**
1. Vite requires environment variables at **build time**, not runtime
2. Cloud Run buildpacks only support **runtime** environment variables
3. The industry-standard solution is **Dockerfile with build args**
4. Always verify the compiled JavaScript contains the correct API URL
5. Browser DevTools Network tab is critical for debugging frontend issues

**Next Steps:**
1. Implement Dockerfile approach as documented
2. Deploy and verify
3. Update documentation (README, deployment guides)
4. Set up monitoring and alerting
5. Create automated tests to catch this issue in future

---

**Document Version:** 1.0
**Last Updated:** December 17, 2025
**Author:** Claude Code (Debugging Assistant)
**Status:** Ready for Implementation
