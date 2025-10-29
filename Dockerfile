# syntax=docker/dockerfile:1

############################
# Builder: produce a wheel #
############################
FROM python:3.11-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /src

COPY pyproject.toml ./
COPY README.md ./
COPY webapp ./webapp

RUN python -m pip install --upgrade pip build hatchling && \
    python -m build --wheel

############################
# Runtime: minimal image   #
############################
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONOPTIMIZE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /src/dist/*.whl /tmp/dist/
RUN python -m pip install --no-cache-dir /tmp/dist/*.whl && rm -rf /tmp/dist

# --- OPTIONAL: verify your LLM instrumentation is present ---
RUN python - <<'PY'
import os, inspect
# Set dummy env vars for Pydantic validation
os.environ.setdefault("OPENAI_API_BASE", "https://example.com")
os.environ.setdefault("OPENAI_API_KEY", "dummy")
os.environ.setdefault("CHAT_DEPLOYMENT", "test-model")
os.environ.setdefault("EMBEDDING_DEPLOYMENT", "test-embed")
os.environ.setdefault("SEARCH_SERVICE_NAME", "dummy-service")
os.environ.setdefault("SEARCH_API_KEY", "dummy-key")
os.environ.setdefault("SEARCH_INDEX_NAME", "dummy-index")

import webapp.services.rag as r
p = inspect.getsourcefile(r)
src = open(p, encoding="utf-8").read()
print("RAG FILE:", p)
print("HAS LLMCallTimer:", "LLMCallTimer" in src)
PY

# Non-root user
RUN useradd -m -u 10001 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

CMD ["uvicorn","webapp.main:app","--host","0.0.0.0","--port","8000","--proxy-headers"]
