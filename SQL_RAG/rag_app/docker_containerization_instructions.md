 Here’s a concrete, end-to-end task list to move from personal → work setup, with clean switching between Ollama and Hugging Face embeddings.

  Repository + Config Baseline

  - Version the repo (or export clean archive) without personal data.
  - Add README_work.md with work-specific steps and environment notes.
  - Add .env.template with placeholders for:
      - EMBEDDINGS_PROVIDER (ollama|huggingface)
      - OLLAMA_BASE_URL
      - HF_EMBEDDING_MODEL, HF_EMBEDDING_DEVICE, HF_CACHE_DIR, TRANSFORMERS_OFFLINE, HF_HUB_OFFLINE
      - GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT + GOOGLE_APPLICATION_CREDENTIALS

  Work Data Preparation

  - Create work input folders on the work laptop:
      - work/lookml_data (your LookML model + views)
      - work/data_new (work schema CSVs)
      - work/sample_queries_with_metadata.csv (work queries dataset)
  - Ensure you can legally transfer no personal data; scrub any residual local caches.

  Containerization (Docker + Compose)

  - Add a Dockerfile for the app:
      - Base python:3.11-slim, install faiss-cpu, graphviz, build deps; pip install -r requirements.txt.
      - CMD ["streamlit","run","app_simple_gemini.py","--server.port=8501","--server.address=0.0.0.0"]
  - Add docker-compose.yml with services:
      - app (Streamlit): mounts volumes and reads env from .env.
      - ollama (only if EMBEDDINGS_PROVIDER=ollama): ollama/ollama:latest, expose 11434.
      - Jobs (profiles):
      - `embedder`: runs `standalone_embedding_generator.py` on demand.
      - `analytics`: runs `catalog_analytics_generator.py` on demand.
  - Define volumes/bind mounts:
      - ./work/faiss_indices:/app/faiss_indices:rw
      - ./work/catalog_analytics:/app/catalog_analytics:rw
      - ./work/data_new:/app/data_new:ro
      - ./work/lookml_data:/app/lookml_data:ro
      - ./models:/models:ro (for Hugging Face local models)

  Embedding Provider Factory (add Hugging Face)

  - Update utils/embedding_provider.py:
      - Add huggingface provider using langchain_community.embeddings.HuggingFaceEmbeddings.
      - Read:
      - `HF_EMBEDDING_MODEL` (accept local path, e.g., `/models/bge-small-en-v1.5`)
      - `HF_EMBEDDING_DEVICE` (`cpu` or `cuda:0`)
      - `HF_CACHE_DIR` (optional)
      - `TRANSFORMERS_OFFLINE=1`, `HF_HUB_OFFLINE=1` (optional)
  - Ensure Ollama path uses OLLAMA_BASE_URL if set.
  - Add deps to requirements.txt:
      - sentence-transformers
      - huggingface-hub (only if you later want inference API; optional now)

  Refactor Embedding Generator To Use Provider

  - Update standalone_embedding_generator.py:
      - Replace direct OllamaEmbeddings with get_embedding_function() (current model/provider from env or CLI).
      - Add CLI flags:
      - `--embedding-provider` (ollama|huggingface)
      - `--embedding-model` (e.g., `/models/bge-small-en-v1.5` or `nomic-embed-text`)
  - Ensure batch workers pass model/provider (remove hard-coded "nomic-embed-text").
  - Keep FAISS GPU/CPU handling intact (works for any embedding backend).
  - Note: FAISS must be rebuilt when switching provider/model (embedding dimensions must match at query-time).

  Local Hugging Face Model (Offline)

  - Pre-download model to host (work laptop):
      - huggingface-cli download BAAI/bge-small-en-v1.5 --local-dir ./models/bge-small-en-v1.5
  - Set .env for HF:
      - EMBEDDINGS_PROVIDER=huggingface
      - HF_EMBEDDING_MODEL=/models/bge-small-en-v1.5
      - HF_EMBEDDING_DEVICE=cpu (or cuda:0)
      - HF_CACHE_DIR=/models/cache (optional)
      - TRANSFORMERS_OFFLINE=1
      - HF_HUB_OFFLINE=1

  Build Vector Store + LookML Map On Work Data

  - Run embedder job (HF example):
      - docker compose run --rm --profile jobs embedder python standalone_embedding_generator.py --csv /app/sample_queries_with_metadata.csv --lookml-dir /app/lookml_data --embedding-provider
  huggingface --embedding-model /models/bge-small-en-v1.5
  - Or Ollama example (if using Ollama at work):
      - Ensure ollama service is up and OLLAMA_BASE_URL=http://ollama:11434.
      - docker compose run --rm --profile jobs embedder python standalone_embedding_generator.py --csv /app/sample_queries_with_metadata.csv --lookml-dir /app/lookml_data --embedding-provider ollama
  --embedding-model nomic-embed-text
  - Result:
      - faiss_indices/index_<csv_name> populated
      - faiss_indices/lookml_safe_join_map.json generated (from work LookML)

  Run The App (Work)

  - Set .env for runtime matching the index provider/model:
      - For HF: same EMBEDDINGS_PROVIDER=huggingface, HF_EMBEDDING_MODEL=...
      - For Ollama: EMBEDDINGS_PROVIDER=ollama, OLLAMA_BASE_URL=http://ollama:11434
      - Schema + LookML mounted via volumes.
      - Gemini:
      - Google AI SDK: `GEMINI_API_KEY=...`
      - Or Vertex: `GOOGLE_CLOUD_PROJECT=...` and mount credentials with `GOOGLE_APPLICATION_CREDENTIALS`.
  - Start:
      - docker compose up app
  - Validate logs:
      - Schema loaded with your work counts
      - LookML safe-join map loaded (explore count)
      - Vector store loaded (doc count) and embedding provider setting
      - Join/SQL questions inject LookML context; @schema queries return direct join details

  Switching Embedding Provider (Ollama ↔ Hugging Face)

  - Change envs in .env:
      - Provider + model settings
  - Rebuild FAISS for the new provider/model with the embedder job.
  - Restart app service with the matching envs.

  Security + Secrets

  - Use .env (not committed) or Docker secrets for:
      - GEMINI_API_KEY or Google credentials file
  - Keep data volumes separate per environment (personal vs work).
  - Confirm no personal data is mounted in work Compose.

  Optional Hardening/Improvements

  - Add docker-compose.prod.yml with read-only mounts for the app (faiss_indices:ro, catalog_analytics:ro).
  - Add Makefile:
      - make embed-ollama, make embed-hf, make up, make down
  - Add a small log in simple_rag_simple_gemini.py:
      - “LookML context added: explore=<...>, joins=...”
  - Add a config toggle to always inject LookML when multiple tables are detected (not only on “join/sql” keywords), if desired.

  This plan gives you a clean, reproducible path to run with work data and switch embedding backends by flipping envs and rebuilding the index. If you want, I can implement the HF provider and generator
  refactor now and add the Dockerfile + compose scaffold.

