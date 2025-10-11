# Retail SQL RAG Demo

This is a minimal Retrieval-Augmented Generation (RAG) demo that lets you ask questions about the **`retail_system`** SQL / Python codebase.

It uses:

* **OpenAI text-embedding-3-small** for embeddings (cloud) — default
* **FAISS** for the in-memory vector store
* **Google Gemini 2.5 Flash** for fast, intelligent answer generation
* A sophisticated RAG engine with hybrid search and smart schema injection

---

## 1  Install Python packages

```bash
python -m venv .venv && source .venv/bin/activate  # optional
pip install -r rag_app/requirements.txt
```

## 2  Set up API keys and embeddings

By default, the system uses OpenAI embeddings and Google Gemini for generation. You can also switch to local Ollama embeddings.

### Option A: OpenAI embeddings (default, recommended)

Use OpenAI's state-of-the-art `text-embedding-3-*` models for high-quality embeddings.

1) **Get your OpenAI API key** from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

2) **Set up environment variables**:

```bash
# Required: OpenAI API key
export OPENAI_API_KEY=sk-your-openai-api-key-here

# Required: Google Gemini API key (for text generation)
export GEMINI_API_KEY=your-gemini-api-key-here

# Optional: Embedding model (default: text-embedding-3-small)
export OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Optional: Provider selection (default: openai)
export EMBEDDINGS_PROVIDER=openai
```

3) **Generate embeddings** using the new OpenAI provider:

```bash
# Generate vector embeddings using OpenAI
python data/standalone_embedding_generator.py --csv "sample_queries_with_metadata.csv"

# Generate analytics cache for fast Query Catalog
python data/catalog_analytics_generator.py --csv "sample_queries_with_metadata.csv"
```

4) **Launch the application**:

```bash
streamlit run app.py
```

### Option B: Local Ollama embeddings (legacy)

For local processing without API costs, you can use Ollama:

```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Download required models
ollama pull nomic-embed-text  # For embeddings

# Set environment to use Ollama
export EMBEDDINGS_PROVIDER=ollama
export OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Generate embeddings locally
python data/standalone_embedding_generator.py --csv "sample_queries_with_metadata.csv"
```

## 3  Use the application

The application provides three interfaces:

1. **🔍 Query Search**: Advanced RAG with Gemini optimization, hybrid search, and smart schema injection
2. **💬 Chat Interface**: ChatGPT-like conversation with specialized agents (@explain, @create, @schema)
3. **📚 Query Catalog**: Browse and search through your SQL query dataset

Access the web interface at: `http://localhost:8501`

The first run will build a FAISS index (stored as `rag_app/faiss_index.pkl`). Subsequent runs load the cached index for faster responses.

---

### Parameters

* `--k` – how many top chunks to retrieve (default **4**)

### Notes

* The local Phi3 model is instructed **not to hallucinate**; it will answer *"I don't know..."* if the context is insufficient.
* The script keeps things simple—no external databases or web servers required. Feel free to adapt it into a web API, Streamlit app, etc. 
