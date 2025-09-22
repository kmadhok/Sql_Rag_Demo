# SQL RAG Application - Complete Setup Guide

## 📋 Overview

This guide provides step-by-step instructions to set up and run your SQL RAG (Retrieval-Augmented Generation) application. Your codebase is **complete and functional** - you have all the necessary components to run a sophisticated RAG system with:

- **Gemini-powered Chat Interface** with specialized agents (@explain, @create, @schema, @longanswer)
- **Smart Schema Injection** (reduces 39K+ schema rows to ~100-500 relevant ones)
- **Hybrid Search** (vector + keyword BM25 search)
- **Query Rewriting** for enhanced retrieval precision
- **GPU-accelerated Embeddings** with Ollama
- **Query Catalog** with pre-computed analytics and visualizations

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    SQL RAG Application                         │
├─────────────────────────────────────────────────────────────────┤
│  app_simple_gemini.py (Main Streamlit App)                    │
│  ├── Chat Interface (💬 with agent keywords)                   │
│  ├── Query Search (🔍 with Gemini optimization)               │
│  └── Query Catalog (📚 with pre-computed analytics)           │
├─────────────────────────────────────────────────────────────────┤
│  Core RAG Engine (simple_rag_simple_gemini.py)                │
│  ├── Gemini Client (gemini_client.py)                         │
│  ├── Hybrid Retriever (hybrid_retriever.py)                   │
│  ├── Query Rewriter (query_rewriter.py)                       │
│  └── Schema Manager (schema_manager.py)                        │
├─────────────────────────────────────────────────────────────────┤
│  Data Processing Pipeline                                       │
│  ├── Embedding Generator (standalone_embedding_generator.py)   │
│  ├── Analytics Generator (catalog_analytics_generator.py)      │
│  └── Data Source Manager (data_source_manager.py)             │
├─────────────────────────────────────────────────────────────────┤
│  Data Files                                                     │
│  ├── sample_queries_with_metadata.csv (Query data)            │
│  └── sample_queries_metadata_schema.csv (Schema data)          │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start (3 Commands)

If you just want to get running quickly:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Gemini API key
export GEMINI_API_KEY="your-api-key-here"

# 3. Run the app
streamlit run app_simple_gemini.py
```

> **Note**: The app will generate embeddings and analytics on first run if they don't exist.

## 📦 Detailed Setup Instructions

### Step 1: Environment Setup

#### 1.1 Python Version
Your application requires **Python 3.12** (as specified in your runtime.txt):

```bash
# Check Python version
python3 --version  # Should show 3.12.x

# If you need to install Python 3.12
# macOS:
brew install python@3.12

# Ubuntu/Debian:
sudo apt update && sudo apt install python3.12
```

#### 1.2 Virtual Environment (Recommended)
```bash
# Create virtual environment
python3 -m venv sql_rag_env

# Activate virtual environment
# macOS/Linux:
source sql_rag_env/bin/activate
# Windows:
sql_rag_env\Scripts\activate

# Verify activation
which python  # Should point to your virtual environment
```

#### 1.3 Install Dependencies
```bash
# Navigate to your app directory
cd /path/to/SQL_RAG/rag_app

# Install all dependencies
pip install -r requirements.txt

# Verify key installations
python3 -c "import streamlit, langchain, google.genai, faiss; print('✅ Core dependencies installed')"
```

### Step 2: API Configuration

#### 2.1 Gemini API Setup
Your app uses Google's Gemini API for LLM capabilities:

1. **Get API Key**:
   - Visit: https://makersuite.google.com/app/apikey
   - Create a new API key
   - Copy the key (starts with `AIza...`)

2. **Set Environment Variable**:
   ```bash
   # Method 1: Export in terminal
   export GEMINI_API_KEY="AIzaSyC..."
   
   # Method 2: Add to ~/.bashrc or ~/.zshrc (persistent)
   echo 'export GEMINI_API_KEY="AIzaSyC..."' >> ~/.bashrc
   source ~/.bashrc
   
   # Method 3: Create .env file in app directory
   echo 'GEMINI_API_KEY=AIzaSyC...' > .env
   ```

3. **Test Connection**:
   ```bash
   python3 gemini_client.py
   # Should show: ✅ gemini-2.5-flash ready
   ```

#### 2.2 Ollama Setup (For Embeddings)
Your app uses Ollama for local embedding generation:

1. **Install Ollama**:
   ```bash
   # macOS:
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Or download from: https://ollama.ai/download
   ```

2. **Start Ollama Service**:
   ```bash
   # Start Ollama server
   ollama serve
   
   # In another terminal, download the embedding model
   ollama pull nomic-embed-text
   
   # Verify model is available
   ollama list
   # Should show: nomic-embed-text
   ```

3. **Optimize for GPU (Optional)**:
   ```bash
   # For better performance with GPU systems
   export OLLAMA_NUM_PARALLEL=16
   export OLLAMA_MAX_LOADED_MODELS=4
   ```

### Step 3: Data Validation

#### 3.1 Verify Data Files
Your app expects these data files (which you already have):

```bash
ls -la sample_queries_with_metadata.csv
# Should show: CSV file with query, description, tables, joins columns

ls -la sample_queries_metadata_schema.csv  
# Should show: CSV file with tableid, columnnames, datatype columns

# Quick validation
head -5 sample_queries_with_metadata.csv
head -5 sample_queries_metadata_schema.csv
```

#### 3.2 Data Format Validation
```bash
# Check your CSV file format
python3 -c "
import pandas as pd

# Check query data
df = pd.read_csv('sample_queries_with_metadata.csv')
print(f'Queries CSV: {len(df)} rows, columns: {list(df.columns)}')
print(f'Required columns present: {all(col in df.columns for col in [\"query\"])}')

# Check schema data
schema_df = pd.read_csv('sample_queries_metadata_schema.csv')
print(f'Schema CSV: {len(schema_df)} rows, columns: {list(schema_df.columns)}')
print(f'Required columns present: {all(col in schema_df.columns for col in [\"tableid\", \"columnnames\", \"datatype\"])}')
"
```

## ⚡ Running the Application

### Step 4: Data Processing Pipeline

#### 4.1 Generate Vector Embeddings
This creates FAISS vector indices for semantic search:

```bash
# Basic usage
python3 standalone_embedding_generator.py --csv "sample_queries_with_metadata.csv"

# With schema enhancement (recommended)
python3 standalone_embedding_generator.py \
  --csv "sample_queries_with_metadata.csv" \
  --schema "sample_queries_metadata_schema.csv"

# High-performance settings (for powerful systems)
python3 standalone_embedding_generator.py \
  --csv "sample_queries_with_metadata.csv" \
  --schema "sample_queries_metadata_schema.csv" \
  --batch-size 300 --workers 16

# Expected output:
# ✅ Loaded vector store: X documents
# 📁 Vector store saved to: faiss_indices/index_sample_queries_with_metadata
```

#### 4.2 Generate Query Catalog Analytics
This pre-computes analytics for the Query Catalog page:

```bash
# Generate analytics cache
python3 catalog_analytics_generator.py --csv "sample_queries_with_metadata.csv"

# Force rebuild if needed
python3 catalog_analytics_generator.py --csv "sample_queries_with_metadata.csv" --force-rebuild

# Expected output:
# 📊 ANALYTICS CACHE GENERATION SUMMARY
# 📁 Cache Directory: catalog_analytics/
# ✅ Ready for fast Streamlit app loading!
```

### Step 5: Launch the Application

```bash
# Start the Streamlit app
streamlit run app_simple_gemini.py

# App will be available at: http://localhost:8501
```

## 🎯 Application Features Guide

### Chat Interface (💬)
**URL**: http://localhost:8501 → Chat tab

**Agent Keywords**:
- Default: Concise 2-3 sentence responses
- `@explain`: Detailed educational explanations 
- `@create`: SQL code generation with examples
- `@schema`: Database schema exploration (bypasses LLM)
- `@longanswer`: Comprehensive detailed analysis

**Example Queries**:
```
# Default mode
"How do I calculate customer lifetime value?"

# Explanation mode
"@explain What's the difference between INNER JOIN and LEFT JOIN?"

# Creation mode  
"@create Write a query to find top 10 customers by revenue"

# Schema exploration
"@schema show columns in orders"
"@schema what tables have customer_id"
```

### Query Search (🔍)
**URL**: http://localhost:8501 → Query Search tab

**Features**:
- **Gemini Mode**: 18.5x better context utilization with 1M token window
- **Hybrid Search**: Vector + keyword search for 20-40% better SQL term matching
- **Query Rewriting**: 25-40% enhanced retrieval precision
- **Smart Schema Injection**: Reduces 39K+ schema to ~100-500 relevant rows

**Configuration Options**:
- **Top-K Results**: 4-200 (recommend 100+ for Gemini mode)
- **Agent Type**: Default, @explain, @create  
- **Search Methods**: Vector only, Hybrid search
- **Optimizations**: Query rewriting, Schema injection

### Query Catalog (📚)
**URL**: http://localhost:8501 → Query Catalog tab

**Pre-computed Analytics**:
- Join complexity analysis and distribution
- Table usage frequency
- Query metadata statistics
- Interactive relationship graphs
- Fast pagination (15 queries per page)

## 🔧 Troubleshooting Guide

### Common Issues and Solutions

#### Issue: "No module named 'X'"
```bash
# Solution: Install missing dependencies
pip install -r requirements.txt

# If specific module missing:
pip install google-generativeai  # For Gemini
pip install rank-bm25           # For hybrid search
pip install faiss-cpu           # For vector store
```

#### Issue: "API key authentication failed"
```bash
# Check if API key is set
echo $GEMINI_API_KEY

# Re-export API key
export GEMINI_API_KEY="your-actual-api-key"

# Test connection
python3 gemini_client.py
```

#### Issue: "Ollama connection failed"
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if not running
ollama serve

# Pull embedding model if missing
ollama pull nomic-embed-text
```

#### Issue: "Vector store not found"
```bash
# Generate embeddings first
python3 standalone_embedding_generator.py --csv "sample_queries_with_metadata.csv"

# Check if files were created
ls -la faiss_indices/
```

#### Issue: "Analytics cache not available"
```bash
# Generate analytics cache
python3 catalog_analytics_generator.py --csv "sample_queries_with_metadata.csv"

# Check if cache was created
ls -la catalog_analytics/
```

#### Issue: "Port 8501 already in use"
```bash
# Run on different port
streamlit run app_simple_gemini.py --server.port 8502

# Or kill existing Streamlit processes
pkill -f streamlit
```

### Performance Optimization

#### For High-End Systems (32GB+ RAM, RTX A1000+):
```bash
# Embedding generation
python3 standalone_embedding_generator.py \
  --csv "sample_queries_with_metadata.csv" \
  --schema "sample_queries_metadata_schema.csv" \
  --batch-size 300 --workers 16

# Set Ollama optimization
export OLLAMA_NUM_PARALLEL=16
```

#### For Mid-Range Systems (16GB RAM):
```bash
# Conservative settings
python3 standalone_embedding_generator.py \
  --csv "sample_queries_with_metadata.csv" \
  --batch-size 150 --workers 8
```

## 📊 Monitoring and Logs

### Application Logs
```bash
# View Streamlit logs
tail -f ~/.streamlit/logs/streamlit.log

# View embedding generation logs  
python3 standalone_embedding_generator.py --verbose --csv "your_file.csv"

# View analytics generation logs
python3 catalog_analytics_generator.py --csv "your_file.csv"
```

### Performance Metrics
The application provides real-time metrics in the UI:
- **Context Usage**: Gemini 1M token window utilization
- **Response Times**: Query processing and generation times
- **Token Counts**: Input/output token usage for cost tracking
- **Search Performance**: Vector vs hybrid search comparisons

## 🔄 Data Updates

### Adding New Queries
```bash
# 1. Update your CSV file with new queries
# 2. Run incremental embedding update
python3 standalone_embedding_generator.py \
  --csv "sample_queries_with_metadata.csv" --incremental

# 3. Regenerate analytics
python3 catalog_analytics_generator.py \
  --csv "sample_queries_with_metadata.csv" --force-rebuild
```

### Schema Updates  
```bash
# 1. Update your schema CSV file
# 2. Rebuild embeddings with new schema
python3 standalone_embedding_generator.py \
  --csv "sample_queries_with_metadata.csv" \
  --schema "sample_queries_metadata_schema.csv" --force-rebuild
```

## 🎉 Success Verification

After completing setup, verify everything works:

1. **✅ Dependencies**: All imports work without errors
2. **✅ API Connection**: Gemini client test passes
3. **✅ Embeddings**: FAISS indices created successfully  
4. **✅ Analytics**: Catalog analytics cache generated
5. **✅ App Launch**: Streamlit app starts without errors
6. **✅ Core Features**: 
   - Chat responds to basic questions
   - Query search returns relevant results
   - Query catalog displays analytics

**Test Query**: Try asking "Show me queries that calculate customer revenue" in the Chat interface.

## 📚 File Structure Reference

Your complete application includes:

### Core Application Files
- `app_simple_gemini.py` - Main Streamlit application
- `simple_rag_simple_gemini.py` - Core RAG engine
- `gemini_client.py` - Gemini API client
- `requirements.txt` - Python dependencies

### Data Processing
- `standalone_embedding_generator.py` - Vector embeddings generation
- `catalog_analytics_generator.py` - Analytics pre-processing  
- `data_source_manager.py` - Data source abstraction

### Advanced Features
- `hybrid_retriever.py` - Vector + keyword search
- `query_rewriter.py` - Query enhancement
- `schema_manager.py` - Smart schema injection

### Data Files
- `sample_queries_with_metadata.csv` - Query dataset
- `sample_queries_metadata_schema.csv` - Database schema

### Generated Assets (created during setup)
- `faiss_indices/` - Vector store files
- `catalog_analytics/` - Pre-computed analytics cache

## 🆘 Getting Help

If you encounter issues:
1. Check this troubleshooting guide first
2. Verify all environment variables are set
3. Ensure all dependencies are installed
4. Check application logs for specific error messages
5. Test individual components using their standalone scripts

Your RAG application is **complete and ready to run** - all the pieces are in place!