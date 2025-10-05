FROM python:3.11-slim

# System deps for faiss, graphviz, and builds
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      graphviz \
      libgomp1 \
      git \
      curl && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_HEADLESS=true

WORKDIR /app

# Install Python deps first (better layer cache)
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app_simple_gemini.py", "--server.port=8501", "--server.address=0.0.0.0"]

