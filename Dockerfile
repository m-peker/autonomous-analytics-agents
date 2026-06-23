FROM python:3.12-slim

LABEL org.opencontainers.image.title="Autonomous Analytics Agents"
LABEL org.opencontainers.image.description="Multi-agent data intelligence platform"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    crawl4ai-setup || true && \
    python -m playwright install --with-deps chromium || true

COPY . .

RUN mkdir -p data/uploads data/outputs data/chroma

# Cloud Run injects PORT=8080; Streamlit defaults to 8501
EXPOSE 8080 8501

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8501}/_stcore/health || exit 1

# Use PORT env var if set (Cloud Run), otherwise default to 8501
CMD streamlit run app/streamlit_app.py \
    --server.address=0.0.0.0 \
    --server.port=${PORT:-8501} \
    --browser.gatherUsageStats=false \
    --server.headless=true
