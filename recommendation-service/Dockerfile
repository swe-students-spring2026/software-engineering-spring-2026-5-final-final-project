# syntax=docker/dockerfile:1.6

FROM python:3.11-slim AS base

# Don't write .pyc files; flush stdout/stderr immediately so logs show up.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies in a separate layer so source changes don't bust the cache.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source.
COPY app ./app
COPY wsgi.py .
COPY scripts ./scripts

# Run as an unprivileged user.
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck talks to our /healthz endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys;\
sys.exit(0) if urllib.request.urlopen('http://localhost:8000/healthz', timeout=3).status==200 else sys.exit(1)" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "wsgi:application"]
