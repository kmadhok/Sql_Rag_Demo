# Retail SQL RAG Demo

This is a minimal Retrieval-Augmented Generation (RAG) demo that lets you ask questions about the **`retail_system`** SQL / Python codebase.



It uses:

* **Sentence-Transformers** (`all-MiniLM-L6-v2`) for embeddings
* **FAISS** for the in-memory vector store
* **Groq** Llama 70B (`llama3-70b-8192`) for answer generation
* A lightweight script `simple_rag.py` to tie everything together

---

## 1  Install Python packages

```bash
python -m venv .venv && source .venv/bin/activate  # optional
pip install -r rag_app/requirements.txt
```

## 2  Set your Groq API key

Export an environment variable `GROQ_API_KEY` *or* create a `.env` file at the project root:

```bash
export GROQ_API_KEY="<your-groq-key>"
```

```
# .env
GROQ_API_KEY=<your-groq-key>
```

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

* The LLM is instructed **not to hallucinate**; it will answer *"I don't know..."* if the context is insufficient.
* The script keeps things simple—no external databases or web servers required. Feel free to adapt it into a web API, Streamlit app, etc. 
