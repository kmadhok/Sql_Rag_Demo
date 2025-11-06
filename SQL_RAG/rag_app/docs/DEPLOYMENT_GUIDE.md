# SQL RAG Application - Google Cloud Run Deployment Guide

This comprehensive guide provides step-by-step instructions for deploying the SQL RAG application to Google Cloud Run with production-ready monitoring, logging, and CI/CD.

## 🚀 Quick Start Deployment

### Prerequisites
- Google Cloud account with billing enabled
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated
- [Docker](https://docs.docker.com/get-docker/) installed
- OpenAI API key
- Google Gemini API key

### One-Command Deployment
```bash
# Run the automated deployment script
./deploy.sh
```

The script will:
1. Check prerequisites
2. Enable required APIs
3. Create Artifact Registry repository
4. Set up secrets in Secret Manager
5. Build and deploy the application
6. Provide the service URL

## 📋 Manual Deployment Steps

### 1. Project Setup

```bash
# Set your Google Cloud project
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com
```

### 2. Create Artifact Registry Repository

```bash
# Create Docker repository
gcloud artifacts repositories create sql-rag-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="SQL RAG Application Container Repository"

# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### 3. Set Up API Keys in Secret Manager

```bash
# Create OpenAI API key secret
echo -n "sk-your-openai-key-here" | gcloud secrets create openai-api-key --data-file=-

# Create Gemini API key secret
echo -n "your-gemini-key-here" | gcloud secrets create gemini-api-key --data-file=-
```

### 4. Build and Deploy Application

Using Cloud Build:
```bash
# Build image using Cloud Build
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/$PROJECT_ID/sql-rag-repo/sql-rag-app:latest

# Deploy to Cloud Run
gcloud run deploy sql-rag-app \
  --image us-central1-docker.pkg.dev/$PROJECT_ID/sql-rag-repo/sql-rag-app:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 10 \
  --min-instances 0 \
  --concurrency 80 \
  --timeout 300 \
  --set-env-vars "PYTHONUNBUFFERED=1,EMBEDDINGS_PROVIDER=openai" \
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest"
```

## 🔧 Local Development Setup

### Quick Setup
```bash
# Run the local setup script
./setup-local.sh
```

### Manual Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Generate embeddings (required for first setup)
python data/standalone_embedding_generator.py --csv "sample_queries_with_metadata.csv"

# Generate analytics cache
python data/catalog_analytics_generator.py --csv "sample_queries_with_metadata.csv"

# Start application
streamlit run app.py
```

## 📊 Monitoring and Logging Setup

### Automated Setup
```bash
# Set up comprehensive monitoring
./setup-monitoring.sh --notification-email your-email@example.com
```

### Manual Monitoring Setup

1. **Enable Monitoring APIs:**
```bash
gcloud services enable \
  monitoring.googleapis.com \
  logging.googleapis.com \
  bigquery.googleapis.com
```

2. **Create BigQuery Datasets:**
```bash
# Error logs dataset
bq mk --dataset --location=US sql_rag_logs

# Metrics dataset  
bq mk --dataset --location=US sql_rag_metrics
```

3. **Create Log Sinks:**
```bash
# Error logs to BigQuery
gcloud logging sinks create sql-rag-error-logs \
  "bigquery.googleapis.com/projects/$PROJECT_ID/datasets/sql_rag_logs" \
  --log-filter='resource.type="cloud_run_revision" severity>=ERROR'

# Metrics to BigQuery
gcloud logging sinks create sql-rag-metrics \
  "bigquery.googleapis.com/projects/$PROJECT_ID/datasets/sql_rag_metrics" \
  --log-filter='resource.type="cloud_run_revision" jsonPayload.type="metrics"'
```

## 🔄 CI/CD Setup

### Using Cloud Build Triggers

1. **Connect GitHub Repository:**
```bash
# Create build trigger (requires GitHub connection)
gcloud builds triggers create github \
  --repo-name=your-repo-name \
  --repo-owner=your-github-username \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

2. **Manual Builds:**
```bash
# Trigger build manually
gcloud builds submit --config=cloudbuild.yaml
```

## 🏗️ Architecture Overview

### Application Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit     │    │   Google        │    │   OpenAI        │
│   Frontend      │ ←→ │   Gemini API    │    │   Embeddings    │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ↓                       ↓                       ↓
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cloud Run     │    │   Secret        │    │   FAISS Vector  │
│   Container     │ ←→ │   Manager       │    │   Store         │
│                 │    │                 │    │   (Memory)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Infrastructure Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cloud Build   │    │   Artifact      │    │   Cloud         │
│   (CI/CD)       │ ←→ │   Registry      │ ←→ │   Run           │
│                 │    │   (Images)      │    │   (Service)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ↓                       ↓                       ↓
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cloud         │    │   BigQuery      │    │   Cloud         │
│   Monitoring    │ ←→ │   (Logs)        │    │   Storage       │
│   (Alerts)      │    │                 │    │   (Security)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 File Structure

### Deployment Files
```
rag_app/
├── Dockerfile                  # Production container configuration
├── .dockerignore              # Build optimization
├── cloudbuild.yaml           # CI/CD pipeline configuration
├── requirements.txt          # Production dependencies
├── deploy.sh                 # Automated deployment script
├── setup-local.sh           # Local development setup
├── setup-monitoring.sh      # Monitoring setup script
├── monitoring.yaml          # Monitoring policies
├── logging.yaml             # Logging configuration
└── DEPLOYMENT_GUIDE.md      # This guide
```

### Environment Configuration
```
├── .env.example             # Environment template
├── .env.development         # Development settings
└── .env.production          # Production settings
```

### Application Files
```
├── app.py                   # Main Streamlit application
├── core/                    # Core business logic
├── modular/                 # UI components
├── utils/                   # Utilities and providers
└── data/                    # Data processing scripts
```

## ⚙️ Configuration Options

### Environment Variables

#### Required (Production)
```bash
OPENAI_API_KEY=sk-your-key      # From Google Secret Manager
GEMINI_API_KEY=your-key         # From Google Secret Manager
EMBEDDINGS_PROVIDER=openai      # Cloud-optimized provider
```

#### Optional (Performance Tuning)
```bash
VECTOR_STORE_BATCH_SIZE=100     # Embedding batch size
MAX_CONCURRENT_REQUESTS=80      # Cloud Run concurrency
REQUEST_TIMEOUT_SECONDS=300     # Request timeout
MAX_MEMORY_USAGE_MB=1800       # Memory limit
```

#### Feature Flags
```bash
ENABLE_ANALYTICS_CACHE=true     # Pre-computed analytics
ENABLE_HYBRID_SEARCH=true       # Vector + keyword search
ENABLE_QUERY_REWRITING=true     # Query enhancement
ENABLE_CHAT_INTERFACE=true      # Chat functionality
```

### Cloud Run Configuration

#### Resource Limits
- **Memory:** 2Gi (configurable up to 8Gi)
- **CPU:** 2 vCPU (configurable up to 4 vCPU)
- **Timeout:** 300 seconds (configurable up to 3600s)
- **Concurrency:** 80 (configurable up to 1000)

#### Scaling Configuration
- **Min Instances:** 0 (cold start optimization)
- **Max Instances:** 10 (cost control)
- **Scaling:** Automatic based on request volume

## 🔒 Security Configuration

### API Key Management
- API keys stored in Google Secret Manager
- Automatic injection via Cloud Run secrets
- No API keys in code or environment files
- Rotation support through Secret Manager versions

### Network Security
- HTTPS enforcement
- Cloud Run IAM authentication (optional)
- CORS and XSRF protection configured
- Request size limits enforced

### Container Security
- Non-root user execution
- Minimal base image (Python 3.11-slim)
- Security updates via base image updates
- Read-only filesystem where possible

## 📈 Monitoring and Alerting

### Key Metrics Monitored
- **Request Rate:** Requests per second
- **Error Rate:** Percentage of failed requests
- **Response Time:** 95th percentile latency
- **Memory Usage:** Container memory utilization
- **API Usage:** OpenAI and Gemini API calls

### Alert Conditions
- Error rate > 5% for 5 minutes
- Response time > 5 seconds for 5 minutes
- Memory usage > 85% for 10 minutes
- Cold starts > 10 per hour

### Log Management
- **Error Logs:** BigQuery (90-day retention)
- **Metrics:** BigQuery (180-day retention)
- **Security Logs:** Cloud Storage (7-year retention)
- **Health Checks:** Excluded from logs (noise reduction)

## 💰 Cost Optimization

### Estimated Monthly Costs (USD)

#### Cloud Run
- **Base Service:** $0 (no traffic)
- **CPU Time:** ~$5-20 (depends on usage)
- **Memory:** ~$2-8 (depends on usage)
- **Requests:** ~$0.40 per million requests

#### APIs
- **OpenAI Embeddings:** $0.02 per 1K tokens (~$0.50-5/month)
- **Google Gemini:** $0.00015 per 1K tokens (~$1-10/month)

#### Storage & Monitoring
- **Artifact Registry:** ~$0.10/GB/month
- **Secret Manager:** $0.06 per 10K accesses
- **BigQuery:** $5/TB stored, $5/TB processed
- **Cloud Logging:** $0.50 per GB ingested

#### Total Estimated Cost
- **Low Usage:** $10-30/month
- **Medium Usage:** $30-100/month
- **High Usage:** $100-300/month

### Cost Optimization Tips
1. **Use min-instances=0** for cost savings (accept cold starts)
2. **Optimize memory allocation** based on actual usage
3. **Use log exclusions** to reduce logging costs
4. **Monitor API usage** and optimize embedding generation
5. **Set up billing alerts** for cost control

## 🚨 Troubleshooting

### Common Deployment Issues

#### Build Failures
```bash
# Check build logs
gcloud builds log BUILD_ID

# Common fixes
- Verify Dockerfile syntax
- Check .dockerignore includes
- Ensure requirements.txt is valid
```

#### Deployment Failures
```bash
# Check Cloud Run logs
gcloud run services logs tail sql-rag-app --region=us-central1

# Common fixes
- Verify API keys in Secret Manager
- Check resource allocations
- Validate environment variables
```

#### Runtime Errors
```bash
# Monitor real-time logs
gcloud logging tail "resource.type=cloud_run_revision"

# Common fixes
- Check OpenAI API key validity
- Verify Gemini API configuration
- Monitor memory usage
- Check embedding model availability
```

### Performance Issues

#### High Latency
1. **Check cold starts:** Increase min-instances
2. **Monitor API calls:** Optimize embedding generation
3. **Review memory:** Increase allocation if needed
4. **Check logs:** Look for timeout errors

#### High Error Rates
1. **Verify API keys:** Check Secret Manager configuration
2. **Monitor quotas:** Check OpenAI/Gemini API limits
3. **Review logs:** Look for specific error patterns
4. **Check dependencies:** Verify package versions

### Health Checks
```bash
# Check service health
curl https://your-service-url/_stcore/health

# Expected response: {"status": "ok"}
```

## 🔄 Updates and Maintenance

### Application Updates
```bash
# Deploy new version
./deploy.sh

# Rollback if needed
gcloud run services update-traffic sql-rag-app \
  --to-revisions=PREVIOUS_REVISION=100
```

### Dependency Updates
```bash
# Update requirements.txt
pip freeze > requirements.txt

# Rebuild and deploy
gcloud builds submit --tag us-central1-docker.pkg.dev/$PROJECT_ID/sql-rag-repo/sql-rag-app:latest
```

### Monitoring Updates
```bash
# Update monitoring configuration
./setup-monitoring.sh
```

## 📞 Support and Resources

### Documentation Links
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Cloud Monitoring Documentation](https://cloud.google.com/monitoring/docs)

### Useful Commands
```bash
# View service details
gcloud run services describe sql-rag-app --region=us-central1

# View recent deployments
gcloud run revisions list --service=sql-rag-app --region=us-central1

# View service URL
gcloud run services describe sql-rag-app --region=us-central1 --format="value(status.url)"

# Scale service
gcloud run services update sql-rag-app --region=us-central1 --max-instances=20

# Update environment variables
gcloud run services update sql-rag-app --region=us-central1 --set-env-vars="NEW_VAR=value"
```

---

**🎉 Congratulations!** Your SQL RAG application is now deployed to Google Cloud Run with enterprise-grade monitoring, logging, and security configurations.