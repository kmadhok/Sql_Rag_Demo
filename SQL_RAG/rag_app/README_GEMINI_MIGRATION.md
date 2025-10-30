# 🔄 Migration to Gemini Embeddings

## 🚨 **Important: Vector Store Dimensionality Change**

When switching from OpenAI to Gemini embeddings, you **must regenerate your vector store** because:

- **OpenAI text-embedding-3-small**: 1536 dimensions
- **Gemini gemini-embedding-001**: 768 dimensions

## 🛠️ **Migration Steps**

### **1. Backup Your Current Setup**
```bash
mv faiss_indices faiss_indices_openai_backup
# Or
cp -r faiss_indices faiss_indices_backup_$(date +%Y%m%d)
```

### **2. Switch to Gemini Embeddings**
```bash
# Set environment variables
export EMBEDDINGS_PROVIDER="gemini"
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export GOOGLE_CLOUD_LOCATION="global"
export GOOGLE_GENAI_USE_VERTEXAI="True"

# Remove OpenAI variables (optional)
unset OPENAI_API_KEY
```

### **3. Regenerate Vector Store**
```bash
# Install required packages if not already installed
pip install --upgrade google-genai

# Run the embedding generator with Gemini
python standalone_embedding_generator.py --csv "your_data.csv" --embeddings-provider gemini

# Or if using the default data
python standalone_embedding_generator.py --embeddings-provider gemini
```

### **4. Verify the Migration**
```bash
# Test the new setup
python app_simple_gemini.py

# Check the logs for:
# "Using Gemini embedding model: gemini-embedding-001"
# "Embeddings initialized successfully"
```

## 🔍 **Verification Commands**

### **Check Current Provider**
```bash
python -c "
from utils.embedding_provider import get_provider_info
info = get_provider_info()
print(f'Provider: {info["provider"]}')
print(f'Model: {info["model"]}')
print(f'Dimensions: {info["dimensions"]}')
print(f'Cloud Ready: {info["cloud_ready"]}')
"
```

### **Test Vector Store Loading**
```bash
python -c "
from data.app_data_loader import load_vector_store
vs = load_vector_store()
if vs:
    print('✅ Vector store loaded successfully')
    print(f'Embedding function: {type(vs.embedding_function)}')
else:
    print('❌ Vector store failed to load')
"
```

## 🚨 **Troubleshooting**

### **Error: "GeminiEmbeddings object is not callable"**

**Cause**: Vector store created with OpenAI, trying to use with Gemini.

**Solution**: Regenerate vector store with Gemini (see steps above).

### **Error: "Dimensionality mismatch"**

**Cause**: Trying to use embeddings with different vector sizes.

**Solution**: Cannot mix embedding providers. Regenerate with consistent provider.

### **Error: "Vertex AI API not enabled"**

**Cause**: GCP project doesn't have Vertex AI enabled.

**Solution**: 
1. Go to Google Cloud Console
2. Enable Vertex AI API for your project
3. Ensure service account has `aiplatform.user` role

## ⚡ **Auto-Migration Script**

Create a migration script to automate the process:

```bash
#!/bin/bash
# migrate_to_gemini.sh

echo "🔄 Migrating to Gemini embeddings..."

# Backup current vector store
if [ -d "faiss_indices" ]; then
    echo "📦 Backing up current vector store..."
    mv faiss_indices faiss_indices_openai_backup_$(date +%Y%m%d_%H%M%S)
fi

# Set environment variables
echo "⚙️ Setting environment variables..."
export EMBEDDINGS_PROVIDER="gemini"
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-your-project-id}"
export GOOGLE_CLOUD_LOCATION="global"
export GOOGLE_GENAI_USE_VERTEXAI="True"

# Regenerate vector store
echo "📚 Regenerating vector store with Gemini..."
python standalone_embedding_generator.py --embeddings-provider gemini

echo "✅ Migration complete!"
echo "🚀 Run: python app_simple_gemini.py"
```

## 📊 **Benefits of Migration**

### **✅ Why Switch to Gemini?**

1. **🏢 Native GCP Integration**: Works seamlessly with Google Cloud
2. **💰 Cost Optimization**: Potentially lower costs with GCP pricing
3. **🔐 Enhanced Security**: Service account authentication (no API keys)
4. **🚀 Performance**: Lower latency for GCP deployments
5. **📏 Simpler**: Fixed 768 dimensions (vs variable OpenAI sizes)
6. **🌐 Unified Stack**: Same provider as your Gemini LLM

### **📈 Performance Comparison**

| Feature | OpenAI | Gemini |
|---------|--------|--------|
| Dimensions | 1536 | 768 |
| Authentication | API Key | GCP Service Account |
| GCP Integration | External | Native |
| Cloud Run Ready | ✅ | ✅ |
| Cost | Higher | Optimized |
| Latency | Variable | Consistent |

## 🎯 **Production Deployment**

For Cloud Run deployment, update your `.env` file:

```bash
# .env for production
EMBEDDINGS_PROVIDER=gemini
GOOGLE_CLOUD_PROJECT=your-production-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=True
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

And update your Cloud Run deployment:

```bash
gcloud run deploy sql-rag-app \n    --set-env-vars="EMBEDDINGS_PROVIDER=gemini" \n    --set-env-vars="GOOGLE_CLOUD_PROJECT=your-production-project-id" \n    --set-env-vars="GOOGLE_CLOUD_LOCATION=us-central1"
```

**🎉 Migration Complete! You're now running with Google Gemini embeddings!**