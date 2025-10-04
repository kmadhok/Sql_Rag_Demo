# Retail SQL RAG Demo

This is a minimal Retrieval-Augmented Generation (RAG) demo that lets you ask questions about the **`retail_system`** SQL / Python codebase.

It uses:

* **Ollama nomic-embed-text** for embeddings (local) — default
* **FAISS** for the in-memory vector store
* **Ollama** Phi3 (3.8B parameters) for local answer generation
* A lightweight script `simple_rag.py` to tie everything together

---

## 1  Install Python packages

```bash
python -m venv .venv && source .venv/bin/activate  # optional
pip install -r rag_app/requirements.txt
```

## 2  Set up embeddings and models

By default, embeddings run locally via Ollama. You can also switch to OpenAI embeddings.

### Option A: Local (default, Ollama)

Install Ollama and download the required models:

```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Download required models
ollama pull phi3              # For LLM inference  
ollama pull nomic-embed-text  # For embeddings

# Verify installation
ollama list
```

No API keys required - all processing happens locally!

### Option B: OpenAI embeddings

Use OpenAI’s `text-embedding-3-*` models for embedding generation and loading.

1) Install deps (already in requirements): `langchain-openai`
2) Export your key and choose provider:

```
export OPENAI_API_KEY=sk-...
export EMBEDDINGS_PROVIDER=openai
# Optional: choose model (default: text-embedding-3-small)
export OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

3) Build a compatible FAISS store from your CSV using OpenAI:

```
python rag_app/openai_embedding_generator.py --csv rag_app/sample_queries_with_metadata.csv
```

This creates `rag_app/faiss_indices/index_sample_queries_with_metadata`, which the app will load.

## 3  Ask questions

```bash
python rag_app/simple_rag.py "Which SQL file shows how to calculate inventory turnover?"
```

Example output:

```
=== Answer ===
The file **inventory_management/inventory_turnover.sql** contains the query that calculates inventory turnover ratios and identifies slow-moving stock.
```

The first run will build a FAISS index (stored as `rag_app/faiss_index.pkl`). Subsequent runs load the cached index for faster responses.

---

### Parameters

* `--k` – how many top chunks to retrieve (default **4**)

### Notes

* The local Phi3 model is instructed **not to hallucinate**; it will answer *"I don't know..."* if the context is insufficient.
* The script keeps things simple—no external databases or web servers required. Feel free to adapt it into a web API, Streamlit app, etc. 
