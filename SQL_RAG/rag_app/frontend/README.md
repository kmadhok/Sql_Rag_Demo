# SQL RAG React Frontend

This React application consumes the FastAPI endpoints defined in `api/main.py`. It lets you:

1. Ask a natural-language question and view the generated answer/SQL.
2. Inspect the source chunks and usage metrics returned by the pipeline.
3. Execute (or dry-run) the SQL against BigQuery and view the results.

## Prerequisites

- Node.js ≥ 18.x
- The FastAPI service running locally (see `uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload`)

## Environment

Copy the example env file:

```bash
cd frontend
cp .env.example .env.local  # adjust VITE_API_BASE_URL if your API runs elsewhere
```

## Install & Run

```bash
cd frontend
npm install
npm run dev
```

Vite will start the dev server on http://localhost:3000 and proxy API calls to the URL configured in `VITE_API_BASE_URL`.

## Build for production

```bash
npm run build
npm run preview   # optional local preview of the built assets
```

## Project Structure

```
frontend/
├── src/
│   ├── App.jsx               # Core layout / routing
│   ├── components/           # Presentational components
│   ├── hooks/                # Custom hooks for API interactions
│   ├── services/             # Fetch helpers
│   ├── styles.css            # Global styles
│   └── main.jsx              # React bootstrapping
├── .env.example              # Frontend environment variables
├── package.json
└── vite.config.js
```

To add new controls (e.g., hybrid search weights) connect the form inputs in `components/QueryForm.jsx` to the FastAPI payload; the back end already supports the full set of options used in Streamlit.
