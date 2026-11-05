# Production image for the AI Trading Terminal.
# Works unchanged on: Render, Railway, Fly.io, Koyeb, HuggingFace Spaces,
# any Docker host, or locally.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    DB_PATH=/data/trader.db

WORKDIR /app

# deps first so code changes don't bust the build cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# writable volume for the SQLite database (survives container restarts
# on hosts that offer a persistent disk)
RUN mkdir -p /data /app/logs
VOLUME ["/data"]

EXPOSE 8000

HEALTHCHECK --interval=60s --timeout=15s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+__import__('os').environ.get('PORT','8000')+'/healthz').status==200 else 1)"

CMD uvicorn aitrader.dashboard.server:api --host 0.0.0.0 --port ${PORT}
