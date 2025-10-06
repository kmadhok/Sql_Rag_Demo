FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential \
    graphviz \
    curl \
    git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Ensure scripts are executable
RUN chmod +x /app/scripts/*.sh || true

# Streamlit config
ENV STREAMLIT_PORT=8502 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Default to Ollama embeddings via separate service (see docker-compose.yml)
ENV EMBEDDINGS_PROVIDER=ollama \
    OLLAMA_BASE_URL=http://ollama:11434

# Expose Streamlit port
EXPOSE 8502

# Default entrypoint just runs Streamlit app; heavy precompute should be done at runtime via scripts/precompute.sh
ENTRYPOINT ["/bin/bash", "/app/scripts/entrypoint.sh"]

