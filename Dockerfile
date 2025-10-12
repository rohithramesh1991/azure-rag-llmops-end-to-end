# syntax=docker/dockerfile:1

########## Builder: produce a wheel ##########
FROM python:3.11.5-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /src

# copy metadata + source (backend needs to see the code to build)
COPY pyproject.toml ./
COPY webapp ./webapp

# build wheel to /src/dist/*.whl
RUN python -m pip install --upgrade build && \
    python -m build

########## Runtime: minimal image ##########
FROM python:3.11.5-slim

# sensible envs for prod
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONOPTIMIZE=1

WORKDIR /app

# install just the wheel (no compilers/tools in final image)
COPY --from=builder /src/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -rf /tmp/*.whl


# drop privileges
RUN useradd -m appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn","webapp.main:app","--host","0.0.0.0","--port","8000"]


# add near the end, before CMD
RUN adduser --disabled-password --gecos "" appuser
USER appuser
