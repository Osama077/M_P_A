FROM python:3.11-slim

# System deps for mplsoccer (shapely/libgeos) and scipy
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only runtime-essential code
COPY api/ api/
COPY pipeline/ pipeline/
COPY utils/ utils/
COPY visualizations/ visualizations/
COPY config.py .

# Copy parquet + model data (tracked via Git LFS)
COPY data/ data/
COPY models/ models/

# Hugging Face Spaces default port
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/')" || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
