FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    PORT=8000

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY requirements.txt ./
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/instance/uploads && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status == 200 else 1)"

CMD ["sh", "-c", "waitress-serve --listen=0.0.0.0:${PORT} wsgi:app"]
