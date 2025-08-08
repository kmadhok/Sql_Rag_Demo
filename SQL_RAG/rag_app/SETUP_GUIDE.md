# SQL RAG System - Complete Setup Guide

## 📋 Overview

This guide provides step-by-step instructions to set up and run the SQL RAG (Retrieval-Augmented Generation) system. The system enables natural language queries over SQL codebases using local Ollama models for privacy and no API costs.

## 🎯 What You'll Get

- **Natural language queries** over your SQL codebase
- **Local AI processing** (no API keys required)
- **Composite embeddings** from query + description + tables + joins  
- **Incremental updates** for efficient processing
- **Web interface** with search and browse functionality
- **CSV/BigQuery data source** flexibility

---

## 🔧 Prerequisites

### System Requirements
- **Python 3.11+** (Python 3.12 recommended)
- **4GB+ RAM** (for Ollama models)
- **2GB+ disk space** (for models and vector storage)
- **macOS, Linux, or Windows** (with WSL recommended for Windows)

### Required Software
- Python package manager (pip)
- Git (for cloning repositories)
- Terminal/Command line access

---

## 📦 Step 1: Python Environment Setup

### Option A: Using pyenv (Recommended)

#### Install pyenv
```bash
# macOS (using Homebrew)
brew install pyenv

# Linux (using curl)
curl https://pyenv.run | bash

# Add to your shell profile (~/.bashrc, ~/.zshrc, etc.)
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

#### Set up Python environment
```bash
# Install Python 3.11 (or later)
pyenv install 3.11.3

# Create virtual environment
pyenv virtualenv 3.11.3 sql_rag

# Activate environment
pyenv activate sql_rag

# Verify installation
python --version  # Should show Python 3.11.3
```

### Option B: Using venv (Alternative)

```bash
# Create virtual environment
python -m venv sql_rag_env

# Activate environment
# macOS/Linux:
source sql_rag_env/bin/activate
# Windows:
sql_rag_env\Scripts\activate

# Verify installation
python --version
```

### Install Python Dependencies

```bash
# Make sure you're in the virtual environment
# Install core dependencies
pip install streamlit pandas langchain-ollama langchain-community faiss-cpu

# Install additional dependencies
pip install sqlparse rapidfuzz python-dotenv pyvis graphviz

# Verify installation
pip list | grep -E "(streamlit|langchain|faiss)"
```

---

## 🤖 Step 2: Ollama Installation & Model Setup

### Install Ollama

#### macOS
```bash
# Download and install from website
curl -fsSL https://ollama.ai/install.sh | sh

# Or using Homebrew
brew install ollama
```

#### Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Windows
1. Download installer from [ollama.ai](https://ollama.ai/download)
2. Run the installer
3. Restart terminal

### Start Ollama Service

```bash
# Start Ollama service (runs in background)
ollama serve
```

**Note**: Keep this terminal open or run as a background service.

### Download Required Models

Open a new terminal and download the required models:

```bash
# Download Phi3 model for text generation (3.8B parameters, ~2.3GB)
ollama pull phi3

# Download nomic-embed-text for embeddings (137M parameters, ~274MB)  
ollama pull nomic-embed-text

# Verify models are downloaded
ollama list
```

You should see output like:
```
NAME                     ID              SIZE      MODIFIED
phi3:latest              a2c89ceaed85    2.3 GB    X minutes ago
nomic-embed-text:latest  0a109f422b47    274 MB    X minutes ago
```

### Test Ollama Installation

```bash
# Test text generation
ollama run phi3 "Hello, how are you?"

# Test embedding (should return without error)
curl -X POST http://localhost:11434/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "nomic-embed-text", "prompt": "test"}'
```

---

## 📊 Step 3: Data Preparation

### CSV File Format

Your CSV file must have these columns:
- **query** (required): SQL query text
- **description** (optional): Human-readable description
- **table** (optional): Tables involved in the query  
- **joins** (optional): Join information

#### Example CSV Structure:
```csv
query,description,table,joins
"SELECT * FROM customers WHERE status = 'active'","Get all active customers","customers",""
"SELECT c.name, o.total FROM customers c JOIN orders o ON c.id = o.customer_id","Customer orders with join","customers,orders","customers.id = orders.customer_id"
```

### Data File Placement

1. **Create your CSV file** with SQL queries and metadata
2. **Place the CSV file** in your preferred location
3. **Note the full path** - you'll need it for configuration

#### Example Locations:
```bash
# Option 1: In project directory
/path/to/SQL_RAG/your_queries.csv

# Option 2: In your home directory  
~/Documents/sql_queries.csv

# Option 3: Anywhere accessible
/Users/username/data/queries.csv
```

---

## 🚀 Step 4: Download & Setup the Application

### Clone the Repository
```bash
# Clone the repository
git clone <repository-url>
cd SQL_RAG/rag_app

# Or if you already have the files, navigate to the directory
cd /path/to/SQL_RAG/rag_app
```

### Configure Data Source

Edit the `app.py` file to point to your CSV file:

```python
# Find this line (around line 156):
csv_path = '/Users/kanumadhok/Sql_Rag_Demo/SQL_RAG/queries_with_descriptions (1).csv'

# Replace with your CSV path:
csv_path = '/path/to/your/queries.csv'
```

### Environment Variables (Optional)

For BigQuery support in the future, create a `.env` file:

```bash
# Create .env file
touch .env

# Add configuration (optional)
echo "BIGQUERY_PROJECT=your-project-id" >> .env
echo "PREFER_BIGQUERY=false" >> .env
```

---

## ▶️ Step 5: Running the Application

### Start the Application

```bash
# Make sure Ollama is running (ollama serve)
# Make sure you're in the virtual environment
# Navigate to the rag_app directory
cd SQL_RAG/rag_app

# Start Streamlit
streamlit run app.py
```

### First Run Process

1. **Initial Embedding Creation**
   - App will process first 100 queries synchronously (30-60 seconds)
   - Remaining queries processed in background
   - Progress shown in UI

2. **Vector Store Creation**
   - FAISS index created and saved locally
   - Subsequent runs will be much faster (incremental updates)

3. **Ready to Use**
   - Web interface opens at `http://localhost:8501`
   - Start asking natural language questions!

### Expected Output

```
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
Network URL: http://192.168.1.xxx:8501

✅ Loaded 1,038 rows from csv_queries_with_descriptions
🔍 Checking for data changes...
✅ Processed 1038 documents in 45.2s
⚡ Background processing: 23.1s
✅ Vector store ready for queries
```

---

## 🎮 Step 6: Using the Application

### Query Search Tab
1. **Enter natural language questions**:
   - "Show me queries that join customers with orders"
   - "Which queries calculate total amounts?"
   - "Find queries that filter by date"

2. **View Results**:
   - AI-generated answer
   - Source SQL queries with context
   - Token usage statistics

### Browse Queries Tab
1. **Explore your SQL catalog**
2. **View join relationships** in interactive graphs
3. **Search by specific terms** across all queries
4. **Browse metadata** (descriptions, tables, joins)

---

## 🔍 Step 7: Verification & Testing

### Basic Functionality Test

```bash
# Run the test suite
python test_smart_processor.py
```

Expected output:
```
🧪 Testing SmartEmbeddingProcessor with CSV data
✅ Small batch completed in 0.9s
✅ Search returned 3 results
✅ Incremental update completed in 0.0s
🎉 All tests PASSED!
```

### Performance Validation

```bash
# Run performance tests  
python performance_comparison.py
```

Expected results:
- **10 docs**: ~0.2s embedding time
- **50 docs**: ~1.3s embedding time  
- **100 docs**: ~2.1s embedding time
- **Incremental updates**: <0.01s (cache hits)

---

## 🔧 Troubleshooting

### Common Issues & Solutions

#### 1. "ModuleNotFoundError: No module named 'langchain_ollama'"
```bash
# Solution: Install missing dependencies
pip install langchain-ollama langchain-community
```

#### 2. "Connection refused to localhost:11434"
```bash
# Solution: Start Ollama service
ollama serve

# Check if running
curl http://localhost:11434/api/tags
```

#### 3. "Model 'phi3' not found"
```bash
# Solution: Download required models
ollama pull phi3
ollama pull nomic-embed-text
ollama list  # Verify
```

#### 4. "CSV file not found"
```bash
# Solution: Check file path in app.py
# Make sure path is absolute and file exists
ls -la /path/to/your/file.csv
```

#### 5. Embedding creation takes too long (>5 minutes)
```bash
# Check Ollama memory usage
ollama ps

# Restart Ollama service
pkill ollama
ollama serve
```

#### 6. "Error: vector store not ready"
```bash
# Solution: Delete and rebuild vector store
rm -rf faiss_indices/
# Restart the application
```

### Performance Optimization

#### Speed up embedding creation:
1. **Reduce initial batch size** in `smart_embedding_processor.py` (line ~270):
   ```python
   initial_batch_size=50  # Instead of 100
   ```

2. **Use smaller CSV for testing**:
   ```python
   test_df = df.head(100)  # Test with first 100 rows
   ```

3. **Monitor system resources**:
   ```bash
   # Check memory usage
   htop  # or top on macOS
   
   # Check disk space
   df -h
   ```

### Logs and Debugging

#### Enable verbose logging:
```python
# Add to top of app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Check log files:
```bash
# Look for error messages
tail -f embedding_status.json
cat smart_embedding_processor.log  # If created
```

---

## 🔄 Advanced Configuration

### BigQuery Integration (Future)

When ready to migrate from CSV to BigQuery:

1. **Set environment variables**:
   ```bash
   export BIGQUERY_PROJECT="your-project-id"
   export PREFER_BIGQUERY="true"
   ```

2. **Install Google Cloud SDK**:
   ```bash
   pip install google-cloud-bigquery
   ```

3. **Update app.py**:
   ```python
   prefer_bigquery=True  # Change from False
   ```

### Custom Model Configuration

To use different Ollama models:

```python
# In smart_embedding_processor.py
embedding_model = "all-MiniLM-L6-v2"  # Alternative embedding model

# In app.py  
OLLAMA_MODEL_NAME = "llama2"  # Alternative generation model
```

### Vector Store Optimization

For large datasets (10,000+ queries):

```python
# In smart_embedding_processor.py
batch_size = 5  # Smaller batches for stability
initial_batch_size = 50  # Smaller initial batch
```

---

## 📚 Additional Resources

### Documentation Files
- `IMPLEMENTATION_SUMMARY.md` - Technical implementation details
- `CLEANUP_ASSESSMENT.md` - Codebase cleanup recommendations  
- `USER_GUIDE.md` - Detailed usage instructions

### External Resources
- [Ollama Documentation](https://ollama.ai/docs)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction.html)
- [FAISS Documentation](https://faiss.ai/cpp_api/files.html)

### Community Support
- [Ollama GitHub](https://github.com/ollama/ollama)
- [LangChain Community](https://github.com/langchain-ai/langchain)
- [Streamlit Community](https://discuss.streamlit.io/)

---

## ✅ Success Checklist

Before you're done, verify:

- [ ] Python virtual environment activated
- [ ] All dependencies installed (`pip list` shows required packages)
- [ ] Ollama service running (`ollama list` shows models)
- [ ] CSV file prepared with correct columns
- [ ] App.py configured with correct CSV path
- [ ] Streamlit app launches without errors
- [ ] Initial embedding creation completes successfully  
- [ ] Query search returns relevant results
- [ ] Browse queries shows your data correctly
- [ ] Test suite passes (`python test_smart_processor.py`)

## 🎉 You're Ready!

Your SQL RAG system is now set up and ready to use. Start exploring your SQL codebase with natural language queries!

**Quick Start Commands**:
```bash
# Start Ollama (if not running)
ollama serve

# Activate environment  
pyenv activate sql_rag  # or source your_venv/bin/activate

# Run application
cd SQL_RAG/rag_app
streamlit run app.py
```

Happy querying! 🚀