# syntax=docker/dockerfile:1

############################
# Builder: produce a wheel #
############################
FROM python:3.11-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /src

# Copy metadata + source for building
COPY pyproject.toml ./
COPY README.md ./
COPY webapp ./webapp

# Build wheel only (skip sdist)
RUN python -m pip install --upgrade pip build && \
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

# Optional: for HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install the wheel without renaming
COPY --from=builder /src/dist/*.whl /tmp/dist/
RUN python -m pip install --no-cache-dir /tmp/dist/*.whl && rm -rf /tmp/dist

# Non-root user
RUN useradd -m -u 10001 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

CMD ["uvicorn","webapp.main:app","--host","0.0.0.0","--port","8000","--proxy-headers"]
