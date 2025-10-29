# syntax=docker/dockerfile:1

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONOPTIMIZE=1

WORKDIR /app

# system deps (optional)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 1) install deps first (leverage cache)
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# 2) copy your source
COPY . /app

# 3) install your package in-place (non-editable so it copies into site-packages)
RUN pip install --no-cache-dir /app

# Sanity check: prove the file contains LLMCallTimer (non-fatal: prints only)
RUN python - <<'PY'
import inspect
import webapp.services.rag as r
p = inspect.getsourcefile(r)
src = open(p, 'r', encoding='utf-8').read()
print("RAG FILE:", p)
print("HAS LLMCallTimer?", "LLMCallTimer" in src)
PY

# Non-root
RUN useradd -m -u 10001 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

CMD ["uvicorn","webapp.main:app","--host","0.0.0.0","--port","8000","--proxy-headers"]
