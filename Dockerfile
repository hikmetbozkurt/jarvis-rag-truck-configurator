FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/storage/huggingface \
    JARVIS_DATA_DIRECTORY=/app/data \
    JARVIS_VECTOR_STORE_DIRECTORY=/app/storage/vector_store \
    JARVIS_TRACE_LOG_PATH=/app/storage/traces/request_traces.jsonl \
    JARVIS_GOLDEN_SET_PATH=/app/evaluation/golden_set.json \
    JARVIS_EVALUATION_REPORT_DIRECTORY=/app/storage/evaluation_reports

WORKDIR /app

COPY requirements.txt .
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-deps .

COPY data ./data
COPY evaluation/golden_set.json ./evaluation/golden_set.json

RUN useradd --create-home jarvis && mkdir -p /app/storage && chown -R jarvis /app/storage
USER jarvis

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

CMD ["jarvis", "serve", "--host", "0.0.0.0", "--port", "8000"]
