# Workstation Setup

This guide walks through preparing a fresh machine to run the SQL RAG application
with the FastAPI backend and React frontend.

## 1. Clone the repository

```bash
git clone <repository-url>
cd SQL_RAG/rag_app
```

## 2. Prepare Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip wheel setuptools
pip install -e .
```

The `pip install -e .` command uses the new `setup.py` to install all backend
dependencies in editable mode so local code changes take effect immediately.

## 3. Configure environment variables

1. Copy the template and fill in the values that apply to your workspace.
   ```bash
   cp .env.example .env
   ```
2. Provide the required credentials:
   - `GEMINI_API_KEY`: API key for Google Gemini models.
   - `GENAI_CLIENT_MODE`: `api` (default) for API key auth, `sdk` to use Vertex AI with Application Default Credentials.
   - `GOOGLE_CLOUD_PROJECT`: Google Cloud project that hosts BigQuery and Vertex AI.
   - `GOOGLE_APPLICATION_CREDENTIALS`: Absolute path to a service-account JSON key
     (alternatively, authenticate with `gcloud auth application-default login`).
   - `BIGQUERY_PROJECT_ID` / `BIGQUERY_DATASET`: Defaults used for SQL execution.
   - `VECTOR_STORE_NAME`: Name of the FAISS index stored under `faiss_indices/`.
3. Optional toggles for embeddings, validation, and model overrides can remain at their defaults.
   Set `GOOGLE_GENAI_USE_VERTEXAI` if you need to override how embeddings authenticate.

## 4. Prepare vector store data

Make sure the FAISS index referenced by `VECTOR_STORE_NAME` exists under
`faiss_indices/`. If you are onboarding a new environment, generate the index using
the provided helper:

```bash
python standalone_embedding_generator.py --csv sample_queries_with_metadata.csv
```

Point the command at your own CSV if you are loading custom data.

## 5. Start the FastAPI backend

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
```

The startup log should confirm that the vector store, schema manager, and BigQuery
executor load successfully.

## 6. Set up the React frontend

```bash
cd frontend
npm install
cat <<'EOF' > .env.local
VITE_API_BASE_URL=http://localhost:8080
EOF
npm run dev -- --host 127.0.0.1 --port 5173
```

The development server runs at <http://127.0.0.1:5173>. Update `VITE_API_BASE_URL`
if your backend is exposed on a different host or port.

## 7. Optional validation

- Run `pytest` to execute the available backend tests.
- Hit `http://localhost:8080/health` to confirm the API is healthy.
- Load the frontend chat tab and issue a simple query to verify end-to-end flow.

You can now repeat these steps on additional machines to create a consistent
development environment.
