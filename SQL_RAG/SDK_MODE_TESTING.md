# Gemini SDK Mode (Vertex AI) Testing Guide

This guide explains how to verify that your application is using Gemini SDK mode (Vertex AI) instead of API key authentication.

## Overview

The application supports two authentication modes for Google Gemini:

1. **API Mode** (default): Uses `GEMINI_API_KEY` for authentication
2. **SDK Mode** (Vertex AI): Uses Google Cloud Application Default Credentials (no API key needed)

## Quick Start

### 1. Configure Environment

Edit `rag_app/.env`:

```bash
# Set SDK mode
GENAI_CLIENT_MODE=sdk
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# Optional: Comment out API key (not needed in SDK mode)
# GEMINI_API_KEY=your-api-key
```

### 2. Authenticate

```bash
# Local development
gcloud auth application-default login

# OR use service account
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### 3. Run Quick Test

```bash
cd rag_app
python test_sdk_mode.py
```

**Expected Output:**
```
✅ CLIENT INITIALIZED SUCCESSFULLY
   Client mode: sdk
   Project ID: your-gcp-project-id
   Location: us-central1

✅ CONNECTION SUCCESSFUL
✅ GENERATION SUCCESSFUL
🎉 SDK MODE IS VERIFIED WORKING!
```

## Testing Tools

### Tool 1: Quick SDK Mode Test (`test_sdk_mode.py`)

**Purpose:** Fast verification that SDK mode is working correctly.

**Features:**
- Checks environment configuration
- Tests client initialization
- Tests Vertex AI connection
- Tests content generation
- Shows clear success/failure messages

**Usage:**
```bash
cd rag_app
python test_sdk_mode.py
```

**When to use:** First time setup, quick verification after config changes.

---

### Tool 2: Log Checker (`check_sdk_logs.py`)

**Purpose:** Inspect initialization logs for all LLM clients.

**Features:**
- Shows environment variables
- Initializes all LLM registry clients (parser, generator, chat, rewriter)
- Verifies all clients use SDK mode
- Displays detailed initialization logs

**Usage:**
```bash
cd rag_app
python check_sdk_logs.py
```

**What to look for:**
```
✅ Gemini client initialized in Vertex SDK mode: gemini-2.5-flash-lite
   (project=your-project-id, location=us-central1)
```

**When to use:** Debugging initialization issues, verifying all clients use same mode.

---

### Tool 3: Comprehensive Test Suite (`tests/test_gemini_sdk_mode.py`)

**Purpose:** Full test coverage with unit and integration tests.

**Features:**
- Unit tests: Mode detection, environment handling, error cases
- Integration tests: Real Vertex AI API calls
- Comparison tests: SDK vs API mode differences

**Usage:**

```bash
cd /Users/kanumadhok/Downloads/code/Sql_Rag_Demo/SQL_RAG

# Unit tests only (fast, no API calls)
pytest tests/test_gemini_sdk_mode.py::TestGeminiSDKMode -v

# Integration tests (slow, requires credentials)
export GOOGLE_CLOUD_PROJECT=your-project-id
gcloud auth application-default login
pytest tests/test_gemini_sdk_mode.py::TestGeminiSDKModeIntegration -v -m integration

# All tests
pytest tests/test_gemini_sdk_mode.py -v
```

**When to use:** Before deploying, CI/CD pipelines, comprehensive validation.

---

### Tool 4: Streamlit App with Console Logs

**Purpose:** Verify SDK mode in the actual application.

**Usage:**
```bash
cd rag_app
streamlit run app_simple_gemini.py
```

**What to check:**
1. Watch console output when app starts
2. Look for multiple lines showing "Vertex SDK mode"
3. Navigate to Query Search and ask a question
4. Verify no API key errors

**When to use:** End-to-end verification, user acceptance testing.

---

### Tool 5: Existing Integration Tests

**Purpose:** Run full RAG pipeline with real components.

**Usage:**
```bash
cd /Users/kanumadhok/Downloads/code/Sql_Rag_Demo/SQL_RAG

# Prerequisites (one-time setup)
export OPENAI_API_KEY=your-openai-key  # For embeddings
export GENAI_CLIENT_MODE=sdk
export GOOGLE_CLOUD_PROJECT=your-project-id
python tests/integration/setup_test_vector_store.py

# Run integration tests
pytest tests/integration/ -v -m integration

# Specific test
pytest tests/integration/test_complete_pipeline.py::TestCompleteRAGPipeline::test_simple_product_query -v
```

**When to use:** Validate complete pipeline with SDK mode.

---

## Environment Variables Reference

### Required for SDK Mode

| Variable | Description | Example |
|----------|-------------|---------|
| `GENAI_CLIENT_MODE` | Authentication mode | `sdk` |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | `my-project-123` |
| `GOOGLE_CLOUD_LOCATION` | Vertex AI region | `us-central1` or `global` |

### Required for API Mode

| Variable | Description | Example |
|----------|-------------|---------|
| `GENAI_CLIENT_MODE` | Authentication mode | `api` (default) |
| `GEMINI_API_KEY` | Gemini API key | `AIzaSy...` |

### Authentication (SDK Mode)

**Local Development:**
```bash
gcloud auth application-default login
```

**Cloud Run / Production:**
```bash
# Option 1: Service account key file
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Option 2: Workload Identity (recommended for Cloud Run)
# Configure in Cloud Run settings
```

---

## Verification Checklist

- [ ] `.env` file has `GENAI_CLIENT_MODE=sdk`
- [ ] `.env` file has `GOOGLE_CLOUD_PROJECT=your-project-id`
- [ ] `.env` file has `GOOGLE_CLOUD_LOCATION=us-central1` (or `global`)
- [ ] Authenticated via `gcloud auth application-default login` OR service account key
- [ ] Vertex AI API enabled in GCP project
- [ ] `python test_sdk_mode.py` passes ✅
- [ ] `python check_sdk_logs.py` shows all clients in SDK mode ✅
- [ ] Streamlit app console logs show "Vertex SDK mode" ✅
- [ ] Integration tests pass: `pytest tests/test_gemini_sdk_mode.py -m integration -v` ✅

---

## Common Issues & Troubleshooting

### Issue: "GOOGLE_CLOUD_PROJECT is required"

**Cause:** Environment variable not set or not loaded.

**Fix:**
```bash
# Check if set
echo $GOOGLE_CLOUD_PROJECT

# Set it
export GOOGLE_CLOUD_PROJECT=your-project-id

# Or add to .env file
echo "GOOGLE_CLOUD_PROJECT=your-project-id" >> rag_app/.env
```

---

### Issue: "DefaultCredentialsError: Could not automatically determine credentials"

**Cause:** Not authenticated with Google Cloud.

**Fix:**
```bash
# Authenticate
gcloud auth application-default login

# OR set service account key
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

---

### Issue: "Client initialized in API mode" (not SDK mode)

**Cause:** `GENAI_CLIENT_MODE` not set or not set to `sdk`.

**Fix:**
```bash
# Check current value
echo $GENAI_CLIENT_MODE

# Set to sdk
export GENAI_CLIENT_MODE=sdk

# Verify .env file
cat rag_app/.env | grep GENAI_CLIENT_MODE
```

---

### Issue: "Vertex AI API has not been used in project"

**Cause:** Vertex AI API not enabled in your GCP project.

**Fix:**
```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com --project=your-project-id

# OR enable via Cloud Console:
# https://console.cloud.google.com/apis/library/aiplatform.googleapis.com
```

---

### Issue: Logs show both "SDK mode" and "API mode"

**Cause:** Some clients initialized before environment variables were set.

**Fix:**
```bash
# Ensure .env is loaded first
# Restart your terminal/IDE
# Run test again
python check_sdk_logs.py
```

---

### Issue: Tests fail with "quota exceeded"

**Cause:** Vertex AI API quota limits reached.

**Fix:**
- Wait a few minutes and retry
- Check quota in Cloud Console: Quotas & System Limits
- Request quota increase if needed
- Use `gemini-2.5-flash-lite` instead of `gemini-2.5-pro` (cheaper)

---

## Test Execution Matrix

| Test Type | Time | API Calls | Requires Auth | Command |
|-----------|------|-----------|---------------|---------|
| Quick Test | 30s | Yes (3-5) | Yes | `python test_sdk_mode.py` |
| Log Checker | 10s | No | Yes | `python check_sdk_logs.py` |
| Unit Tests | 5s | No | No | `pytest tests/test_gemini_sdk_mode.py::TestGeminiSDKMode` |
| Integration Tests | 2min | Yes (10+) | Yes | `pytest tests/test_gemini_sdk_mode.py::TestGeminiSDKModeIntegration -m integration` |
| Full Pipeline Tests | 5min | Yes (20+) | Yes | `pytest tests/integration/ -m integration` |

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test SDK Mode

on: [push, pull_request]

jobs:
  test-sdk-mode:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r rag_app/requirements.txt
          pip install -r requirements-test.txt

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Run SDK mode tests
        env:
          GENAI_CLIENT_MODE: sdk
          GOOGLE_CLOUD_PROJECT: ${{ secrets.GCP_PROJECT_ID }}
          GOOGLE_CLOUD_LOCATION: us-central1
        run: |
          pytest tests/test_gemini_sdk_mode.py -v
```

---

## Cost Comparison

### API Mode (API Key)
- Pay-per-use pricing from Google AI Studio
- Typically higher per-token cost
- No GCP project required

### SDK Mode (Vertex AI)
- Enterprise pricing (often lower per-token)
- Requires GCP project with billing enabled
- Access to Vertex AI features (monitoring, logging, etc.)

**Recommendation:** Use SDK mode for production deployments on GCP.

---

## Next Steps

After verifying SDK mode works:

1. **Update deployment scripts** to use SDK mode in Cloud Run
2. **Update documentation** to reflect SDK mode as default
3. **Set up monitoring** in Vertex AI for production usage
4. **Configure alerts** for quota limits and errors
5. **Review IAM permissions** for service accounts

---

## Support

If you encounter issues:

1. Run diagnostic: `python check_sdk_logs.py`
2. Check logs: `python test_sdk_mode.py`
3. Verify auth: `gcloud auth application-default print-access-token`
4. Check API enabled: `gcloud services list --enabled | grep aiplatform`
5. Review project: `gcloud config get-value project`

For more help, see:
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Google Gen AI SDK Docs](https://cloud.google.com/vertex-ai/generative-ai/docs/sdks/overview)
- Project CLAUDE.md file for architecture details
