# syntax=docker/dockerfile:1

############################
# Builder: produce a wheel #
############################
FROM python:3.11-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /src

# Copy metadata + source to build the wheel
COPY pyproject.toml ./
COPY webapp ./webapp

# Build wheel into /src/dist/*.whl
RUN python -m pip install --upgrade pip build && \
    python -m build

############################
# Runtime: minimal image   #
############################
FROM python:3.11-slim

# Sensible envs for prod
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONOPTIMIZE=1

WORKDIR /app

# (Optional) install curl for the healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install just the wheel (no compilers/tools in the final image)
COPY --from=builder /src/dist/*.whl /tmp/app.whl
RUN python -m pip install --no-cache-dir /tmp/app.whl && rm -f /tmp/app.whl

# Create non-root user (single, consistent command)
RUN useradd -m -u 10001 appuser
USER appuser

EXPOSE 8000

# Optional: container health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

# Start server
CMD ["uvicorn", "webapp.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
