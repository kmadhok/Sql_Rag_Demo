# Google Gemini + BigQuery Configuration Guide

## 📋 Overview

This guide provides step-by-step instructions to configure the SQL RAG system to use **Google Gemini** as the LLM (instead of Ollama) and load data from a **BigQuery table** (instead of CSV files). This configuration is ideal for production environments with enterprise data sources.

---

## 🔧 Prerequisites

### Google Cloud Requirements
- **Google Cloud Project** with billing enabled
- **BigQuery API** enabled
- **Vertex AI API** enabled
- **Service Account** with appropriate permissions
- **BigQuery dataset and table** with your SQL queries

### Required Permissions
Your service account needs these IAM roles:
- `roles/bigquery.user` - Query BigQuery tables
- `roles/bigquery.dataViewer` - Read BigQuery data  
- `roles/aiplatform.user` - Access Vertex AI/Gemini APIs
- `roles/ml.developer` - Use AI/ML services

---

## 📦 Step 1: Install Required Dependencies

```bash
# Activate your Python environment
pyenv activate sql_rag  # or source your_venv/bin/activate

# Install Google Cloud packages
pip install google-cloud-bigquery google-genai google-cloud-aiplatform

# Verify installation
pip list | grep -E "(google-cloud|genai)"
```

---

## 🔐 Step 2: Authentication Setup

### Create Service Account
```bash
# Create service account
gcloud iam service-accounts create sql-rag-service \
    --description="Service account for SQL RAG application" \
    --display-name="SQL RAG Service Account"

# Grant required permissions
gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
    --member="serviceAccount:sql-rag-service@YOUR-PROJECT-ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.user"

gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
    --member="serviceAccount:sql-rag-service@YOUR-PROJECT-ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
    --member="serviceAccount:sql-rag-service@YOUR-PROJECT-ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

### Download Service Account Key
```bash
# Download service account key
gcloud iam service-accounts keys create ~/sql-rag-key.json \
    --iam-account=sql-rag-service@YOUR-PROJECT-ID.iam.gserviceaccount.com

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/sql-rag-key.json"
```

### Test Authentication
```bash
# Test BigQuery access
bq query --use_legacy_sql=false 'SELECT 1 as test'

# Test Vertex AI access (should not error)
gcloud ai models list --region=us-central1
```

---

## 📊 Step 3: BigQuery Table Setup

### Required Table Schema
Your BigQuery table must have these columns:

```sql
CREATE TABLE `your-project.your_dataset.sql_queries` (
    query STRING NOT NULL,
    description STRING,
    table STRING,
    joins STRING
);
```

### Sample Data Insert
```sql
INSERT INTO `your-project.your_dataset.sql_queries` (query, description, table, joins) VALUES
('SELECT * FROM customers WHERE status = "active"', 'Get all active customers', 'customers', ''),
('SELECT c.name, o.total FROM customers c JOIN orders o ON c.id = o.customer_id', 'Customer orders with join', 'customers,orders', 'c.id = o.customer_id'),
('SELECT COUNT(*) FROM orders WHERE order_date >= "2024-01-01"', 'Count orders from this year', 'orders', '');
```

### Verify Data
```sql
-- Test your table
SELECT COUNT(*) as total_queries FROM `your-project.your_dataset.sql_queries`;
SELECT * FROM `your-project.your_dataset.sql_queries` LIMIT 5;
```

---

## ⚙️ Step 4: Environment Configuration

### Create `.env` file in `/rag_app/` directory:
```bash
# Create environment file
cat > .env << EOF
# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/sql-rag-key.json
BIGQUERY_PROJECT=your-project-id
BIGQUERY_QUERY=SELECT query, description, table, joins FROM \`your-project.your_dataset.sql_queries\`

# Gemini Configuration  
GENAI_PROJECT=your-project-id
GENAI_LOCATION=us-central1

# Data Source Preferences
PREFER_BIGQUERY=true
EOF
```

**Important**: Replace `your-project-id`, `your_dataset`, and the path to your service account key file.

---

## 🔧 Step 5: Code Modifications

### **File 1: `app.py` - Data Source Configuration**

#### **Lines 156-167: Replace CSV configuration with BigQuery**

**FIND THIS CODE:**
```python
csv_path = '/Users/kanumadhok/Sql_Rag_Demo/SQL_RAG/queries_with_descriptions (1).csv'

# Try to detect BigQuery first, fall back to CSV
try:
    data_source = DataSourceManager.auto_detect_source(
        csv_path=csv_path,
        bigquery_project=os.getenv('BIGQUERY_PROJECT'),  # From environment
        prefer_bigquery=False  # Prefer CSV for now, change to True for production
    )
except Exception:
    # Direct CSV fallback
    data_source = DataSourceManager.create_csv_source(csv_path)
```

**REPLACE WITH:**
```python
# BigQuery configuration - no CSV fallback needed
try:
    data_source = DataSourceManager.create_bigquery_source(
        project_id=os.getenv('BIGQUERY_PROJECT'),
        query=os.getenv('BIGQUERY_QUERY')
    )
except Exception as e:
    st.error(f"❌ Failed to connect to BigQuery: {e}")
    st.error("Check your GOOGLE_APPLICATION_CREDENTIALS and BigQuery configuration")
    st.stop()
```

#### **Lines 252-261: Replace Ollama check with Gemini check**

**FIND THIS CODE:**
```python
try:
    from actions.ollama_llm_client import check_ollama_availability
    available, status_msg = check_ollama_availability()
    if not available:
        st.error(f"❌ Ollama not available: {status_msg}")
        st.stop()
    else:
        st.info(f"✅ Ollama status: {status_msg}")
except Exception as e:
    st.warning(f"⚠️ Could not check Ollama status: {e}")
```

**REPLACE WITH:**
```python
try:
    from actions.llm_interaction import initialize_llm_client
    llm_client = initialize_llm_client()
    st.info(f"✅ Google Gemini client initialized")
except Exception as e:
    st.error(f"❌ Google Gemini not available: {e}")
    st.error("Check your Google Cloud authentication and Vertex AI API access")
    st.stop()
```

### **File 2: `simple_rag.py` - LLM Configuration**

#### **Line 13: Update imports**

**FIND THIS CODE:**
```python
from actions import build_or_load_vector_store, _create_embedding_batch,_create_embeddings_parallel,generate_answer_with_ollama
```

**REPLACE WITH:**
```python
from actions import build_or_load_vector_store, _create_embedding_batch,_create_embeddings_parallel,generate_answer_from_context
```

#### **Line 22: Add Gemini model configuration**

**ADD THIS CODE AFTER LINE 22:**
```python
# Gemini model configuration
GENAI_MODEL_NAME = "gemini-2.5-flash-lite"
```

#### **Line 1002: Replace Ollama call with Gemini**

**FIND THIS CODE:**
```python
answer_text, token_usage = generate_answer_with_ollama(query, context, model_name=OLLAMA_MODEL_NAME)
```

**REPLACE WITH:**
```python
answer_text, token_usage = generate_answer_from_context(query, context, model_name=GENAI_MODEL_NAME)
```

### **File 3: `actions/__init__.py` - Update Exports**

#### **Lines 16-21: Replace Ollama imports**

**FIND THIS CODE:**
```python
from .ollama_llm_client import (
    generate_answer_with_ollama,
    initialize_ollama_client,
    check_ollama_availability,
    list_available_phi3_models
)
```

**REPLACE WITH:**
```python
from .llm_interaction import (
    generate_answer_from_context,
    initialize_llm_client
)
```

#### **Lines 39-43: Update __all__ exports**

**FIND THIS CODE:**
```python
"generate_answer_with_ollama",
"initialize_ollama_client", 
"check_ollama_availability",
"list_available_phi3_models",
```

**REPLACE WITH:**
```python
"generate_answer_from_context",
"initialize_llm_client",
```

### **File 4: `actions/llm_interaction.py` - Update Configuration**

#### **Line 23: Update project ID**

**FIND THIS CODE:**
```python
project="wmt-dv-bq-analytics",
```

**REPLACE WITH:**
```python
project=os.getenv('GENAI_PROJECT'),
```

#### **Line 24: Update location**

**FIND THIS CODE:**
```python
location="global",
```

**REPLACE WITH:**
```python
location=os.getenv('GENAI_LOCATION', 'us-central1'),
```

#### **Add imports at top of file:**

**ADD AFTER EXISTING IMPORTS:**
```python
import os
```

### **File 5: `smart_embedding_processor.py` - Embedding Configuration**

You have two options for embeddings:

#### **Option 1: Keep Ollama for embeddings (Recommended)**
- Keep the existing `OllamaEmbeddings(model="nomic-embed-text")` on line 42
- Only use Gemini for text generation, keep Ollama for embeddings
- This provides better performance and lower costs

#### **Option 2: Switch to Google embeddings**

**FIND LINE 42:**
```python
self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
```

**REPLACE WITH:**
```python
from langchain_google_genai import GoogleGenerativeAIEmbeddings
self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
```

**Note**: Option 1 is recommended because Google's embedding API has higher costs and rate limits.

---

## ▶️ Step 6: Running the Application

### Set Environment Variables
```bash
# Set authentication
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/sql-rag-key.json"

# Load environment variables
source .env  # or manually export each variable
```

### Start the Application
```bash
# Navigate to app directory
cd SQL_RAG/rag_app

# Start Streamlit with BigQuery + Gemini
streamlit run app.py
```

### Expected Output
```
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501

✅ Loaded 1,038 rows from bq_sql_queries
✅ Google Gemini client initialized
🔍 Checking for data changes...
✅ Processed 1038 documents in 45.2s
✅ Vector store ready for queries
```

---

## 🧪 Step 7: Testing & Verification

### Test BigQuery Connection
```python
# Test script: test_bigquery_connection.py
from data_source_manager import DataSourceManager
import os

data_source = DataSourceManager.create_bigquery_source(
    project_id=os.getenv('BIGQUERY_PROJECT'),
    query=os.getenv('BIGQUERY_QUERY')
)

df = data_source.load_data()
print(f"✅ Loaded {len(df)} rows from BigQuery")
print(f"Columns: {list(df.columns)}")
```

### Test Gemini LLM
```python
# Test script: test_gemini_llm.py
from actions.llm_interaction import generate_answer_from_context

query = "What queries join customers with orders?"
context = "SELECT c.name, o.total FROM customers c JOIN orders o ON c.id = o.customer_id"

answer, tokens = generate_answer_from_context(query, context)
print(f"✅ Gemini response: {answer[:100]}...")
print(f"✅ Token usage: {tokens}")
```

### Test Complete System
1. **Launch the app**: `streamlit run app.py`
2. **Ask a question**: "Show me queries that calculate totals"
3. **Verify results**: Should show relevant SQL queries with Gemini-generated explanations
4. **Check costs**: Monitor usage in Google Cloud Console

---

## 💰 Step 8: Cost Management

### Gemini Pricing (as of 2024)
- **Input tokens**: $0.00025 per 1K tokens
- **Output tokens**: $0.00075 per 1K tokens
- **Typical query**: 500-2000 tokens total
- **Estimated cost**: $0.001-$0.002 per query

### BigQuery Pricing
- **Query processing**: $6.25 per TB processed
- **Storage**: $0.023 per GB per month
- **Typical usage**: <$1 per month for small datasets

### Cost Optimization
1. **Cache responses** for repeated queries
2. **Use shorter prompts** to reduce token usage
3. **Implement query batching** for bulk operations
4. **Set up billing alerts** in Google Cloud Console

---

## 🔍 Step 9: Troubleshooting

### Common Issues

#### **Authentication Error**
```
Error: google.auth.exceptions.DefaultCredentialsError
```
**Solution:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/correct/path/to/key.json"
gcloud auth application-default login
```

#### **BigQuery Permission Denied**
```
Error: 403 Forbidden: Access Denied
```
**Solution:**
```bash
# Grant required permissions
gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
    --member="serviceAccount:YOUR-SERVICE-ACCOUNT@YOUR-PROJECT-ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.user"
```

#### **Gemini API Not Available**
```
Error: Vertex AI API has not been used in project
```
**Solution:**
```bash
# Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable generativelanguage.googleapis.com
```

#### **Table Not Found**
```
Error: Table 'project.dataset.table' not found
```
**Solution:**
- Verify table exists: `bq ls your-project:your_dataset`
- Check table name in BIGQUERY_QUERY environment variable
- Ensure proper dataset permissions

### Performance Issues

#### **Slow BigQuery Queries**
```sql
-- Optimize your query with LIMIT for testing
SELECT query, description, table, joins 
FROM `your-project.your_dataset.sql_queries`
LIMIT 1000;  -- Add LIMIT for testing
```

#### **High Gemini Costs**
```python
# In actions/llm_interaction.py, line 51
system_prompt = """You are a concise SQL expert. 
Provide brief, direct answers about SQL queries."""  # Shorter prompt
```

---

## 🚀 Step 10: Production Deployment

### Security Best Practices
1. **Use Workload Identity** instead of service account keys
2. **Store secrets** in Google Secret Manager
3. **Enable audit logging** for API access
4. **Set up VPC** for network security

### Monitoring & Alerts
```bash
# Set up billing alerts
gcloud alpha billing budgets create \
    --billing-account=YOUR-BILLING-ACCOUNT \
    --display-name="SQL RAG Budget" \
    --budget-amount=100 \
    --threshold-rule=percent=50,basis=current-spend
```

### Scaling Configuration
```python
# In smart_embedding_processor.py
# For larger datasets, increase batch sizes
initial_batch_size = 500  # Increase from 100
max_workers = 8  # Increase parallel processing
```

---

## ✅ Migration Checklist

### Pre-Migration
- [ ] Google Cloud project setup and billing enabled
- [ ] Service account created with proper permissions  
- [ ] BigQuery table created and populated
- [ ] Authentication tested and working
- [ ] Environment variables configured

### Code Changes
- [ ] Updated `app.py` data source configuration
- [ ] Modified `simple_rag.py` LLM imports and calls
- [ ] Updated `actions/__init__.py` exports
- [ ] Configured `actions/llm_interaction.py` project settings
- [ ] Set embedding strategy in `smart_embedding_processor.py`

### Testing
- [ ] BigQuery connection test passes
- [ ] Gemini LLM response test passes  
- [ ] Complete application launches successfully
- [ ] Sample queries return correct results
- [ ] Cost monitoring configured

### Production Readiness
- [ ] Security best practices implemented
- [ ] Monitoring and alerting configured
- [ ] Cost budgets and alerts set up
- [ ] Backup and recovery plan documented
- [ ] Performance benchmarks established

---

## 🎉 Success!

You now have a production-ready SQL RAG system using:
- **Google Gemini** for intelligent question answering
- **BigQuery** for scalable data storage and querying
- **Enterprise security** with proper authentication
- **Cost monitoring** and optimization

Your system can now handle enterprise-scale SQL query datasets with powerful AI capabilities while maintaining security and cost control.

**Next Steps**: 
- Monitor usage and costs in Google Cloud Console
- Expand your BigQuery dataset with more SQL queries
- Optimize performance based on usage patterns
- Consider implementing caching for frequently asked questions