# 🧠 Gemini Embeddings Setup Guide

This guide covers the setup and configuration of **Google Gemini embeddings** for the SQL RAG application. Gemini embeddings are now the **default and recommended** choice for production deployment on Google Cloud Run.

## 🎯 Why Gemini Embeddings?

### ✅ **Advantages over OpenAI Embeddings**

1. **🏢 Native GCP Integration**: Works seamlessly with Google Cloud infrastructure
2. **💰 Cost-Effective**: Competitive pricing with Google Cloud discounts
3. **🔐 Unified Authentication**: Uses GCP service accounts, no API keys to manage
4. **🌐 Global Performance**: Low-latency access via Vertex AI endpoints
5. **📏 Consistent Dimensions**: Fixed 768-dimensional embeddings for simplicity
6. **🛡️ Enterprise Security**: Built-in Google Cloud security and compliance

## 🛠️ **Installation & Dependencies**

The required package is already included in `requirements.txt`:

```txt
google-genai>=1.0.0,<2.0.0
```

To install/update:

```bash
pip install --upgrade google-genai
```

## ⚙️ **Environment Configuration**

### **Required Environment Variables**

```bash
# Set Gemini as the default embedding provider
export EMBEDDINGS_PROVIDER="gemini"

# Your Google Cloud Project ID
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"

# Cloud region (optional, defaults to "global")
export GOOGLE_CLOUD_LOCATION="global"

# Use Vertex AI (recommended for production)
export GOOGLE_GENAI_USE_VERTEXAI="True"

# Embedding model (optional, default is recommended)
export GEMINI_EMBEDDING_MODEL="gemini-embedding-001"
```

### **Local Development Setup**

1. **Install Google Cloud CLI**:
   ```bash
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   ```

2. **Authenticate**:
   ```bash
   gcloud auth application-default login
   gcloud config set project your-gcp-project-id
   ```

3. **Set Environment Variables**:
   ```bash
   export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
   export EMBEDDINGS_PROVIDER="gemini"
   ```

### **Cloud Run Deployment Setup**

1. **IAM Role**: Ensure your service account has the `aiplatform.user` role:
   ```bash
   gcloud projects add-iam-policy-binding your-gcp-project-id \n       --member="serviceAccount:your-service-account@your-gcp-project-id.iam.gserviceaccount.com" \n       --role="roles/aiplatform.user"
   ```

2. **Environment Variables in Cloud Run**:
   ```bash
   gcloud run deploy sql-rag-app \n       --set-env-vars="EMBEDDINGS_PROVIDER=gemini" \n       --set-env-vars="GOOGLE_CLOUD_PROJECT=your-gcp-project-id" \n       --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=True"
   ```

## 🧪 **Testing the Integration**

Run the test script to verify your setup:

```bash
python test_gemini_embeddings.py
```

Expected output:
```
Provider Info:
  provider: gemini
  model: gemini-embedding-001
  project_id: your-gcp-project-id
  use_vertexai: True
  api_key_configured: True
  cloud_ready: True
  dimensions: 768

✅ Query embedding shape: 768 dimensions
✅ First 5 values: [-0.0630, 0.0092, 0.0147, -0.0287, ...]
✅ Cosine similarity between query and first doc: 0.7234

🎉 Gemini embeddings test completed successfully!
```

## 📊 **Embedding Specifications**

| Property | Value | Description |
|----------|-------|-------------|
| **Model** | `gemini-embedding-001` | Production-optimized Gemini model |
| **Dimensions** | 768 | Fixed dimensional space for consistency |
| **Max Input Length** | ~8,192 tokens | Safe limit for most documents |
| **Batch Size** | 100 texts | Optimized for Vertex AI rate limits |
| **Task Types** | `RETRIEVAL_DOCUMENT`, `RETRIEVAL_QUERY` | Optimized for RAG use cases |

## 🔧 **Technical Implementation**

### **LangChain Compatibility**
The Gemini embeddings are wrapped in a custom `GeminiEmbeddings` class that provides full LangChain compatibility:

```python
from utils.embedding_provider import get_embedding_function

# Initialize Gemini embeddings
embeddings = get_embedding_function(provider="gemini")

# Use like any LangChain embeddings
query_embedding = embeddings.embed_query("Your query here")
doc_embeddings = embeddings.embed_documents(["Document 1", "Document 2"])
```

### **Automatic Task Type Handling**
The wrapper automatically uses the correct task type:
- `RETRIEVAL_DOCUMENT` for batch documents (indexing)
- `RETRIEVAL_QUERY` for single queries (searching)

### **Error Handling & Logging**
Comprehensive error handling with detailed troubleshooting information:
- Missing environment variables
- Authentication failures
- Rate limit handling
- Batch processing errors

## 🚀 **Migration from OpenAI**

### **Simple Switch**
Just change your environment variable:

```bash
# From OpenAI
# export EMBEDDINGS_PROVIDER="openai"
# export OPENAI_API_KEY="sk-..."

# To Gemini  
export EMBEDDINGS_PROVIDER="gemini"
export GOOGLE_CLOUD_PROJECT="your-project-id"
# No API key needed - uses GCP authentication!
```

### **Dimension Compatibility**
- **OpenAI text-embedding-3-small**: 1536 dimensions
- **OpenAI text-embedding-3-large**: 3072 dimensions  
- **Gemini gemini-embedding-001**: 768 dimensions

**Note**: You'll need to regenerate your vector store when switching providers due to different dimensional spaces.

## 🆘 **Troubleshooting**

### **Common Issues & Solutions**

1. **"GOOGLE_CLOUD_PROJECT not set"**
   ```bash
   export GOOGLE_CLOUD_PROJECT="your-actual-project-id"
   ```

2. **"Authentication failed"**
   ```bash
   gcloud auth application-default login
   gcloud config set project your-project-id
   ```

3. **"Permission denied"**
   ```bash
   # Grant aiplatform.user role to service account
   gcloud projects add-iam-policy-binding your-project-id \n       --member="serviceAccount:your-service-account@your-project-id.iam.gserviceaccount.com" \n       --role="roles/aiplatform.user"
   ```

4. **"ModuleNotFoundError: No module named 'google.genai'"**
   ```bash
   pip install --upgrade google-genai
   ```

5. **Rate Limits**
   - The implementation includes automatic batching
   - Default batch size is 100 texts
   - Implements retry logic for failed requests

### **Debug Mode**
Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Test embeddings with debug output
embeddings = get_embedding_function(provider="gemini")
```

## 📈 **Performance Tips**

### **Production Optimization**

1. **Batch Processing**: Use `embed_documents()` for multiple texts
2. **Region Selection**: Choose the nearest GCP region for lower latency
3. **Service Account**: Use dedicated service account with minimal permissions
4. **Monitoring**: Monitor Vertex AI quota usage and costs

### **Cost Management**

```bash
# Check Vertex AI pricing and quotas
gcloud ai endpoints list --region=global
gcloud logging read 'resource.type="aiplatform.googleapis.com/Endpoint"' --limit=10
```

## 🎯 **Best Practices**

### **Security**
- ✅ Use service accounts, not API keys
- ✅ Apply principle of least privilege
- ✅ Enable audit logging for production
- ✅ Store sensitive data in Google Secret Manager

### **Performance**
- ✅ Batch embeddings when possible
- ✅ Cache frequently used embeddings
- ✅ Use appropriate regions for your users
- ✅ Monitor latency and error rates

### **Reliability**
- ✅ Implement retry logic
- ✅ Set appropriate timeouts
- ✅ Handle rate limits gracefully
- ✅ Use health checks for deployment

## 🎉 **Ready for Production!**

With Gemini embeddings properly configured, your SQL RAG application is ready for:
- ✅ Google Cloud Run deployment
- ✅ Enterprise-grade security
- ✅ Global scalability
- ✅ Cost optimization
- ✅ Unified GCP stack management

**Happy embedding with Google Gemini!** 🚀