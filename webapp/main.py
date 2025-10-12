# webapp/main.py
from __future__ import annotations

import os
import uuid
import logging
from typing import Any, List, cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, Field, AnyHttpUrl, ValidationError, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from prometheus_fastapi_instrumentator import Instrumentator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from openai import AzureOpenAI, APIError, RateLimitError, APITimeoutError
from openai.types.chat import ChatCompletionMessageParam
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch


# ---------------------------------------------------------------------
# Settings (reads env; .env used locally via env_file, prod uses K8s envs)
# ---------------------------------------------------------------------
class Settings(BaseSettings):
    # Azure AI Foundry project endpoint — MUST include /openai
    OPENAI_API_BASE: AnyHttpUrl
    OPENAI_API_KEY: str
    OPENAI_API_VERSION: str = "2024-06-01"

    # Deployments (Foundry deployment names)
    CHAT_DEPLOYMENT: str
    EMBEDDING_DEPLOYMENT: str

    # Azure AI Search
    SEARCH_SERVICE_NAME: AnyHttpUrl  # e.g., https://<name>.search.windows.net
    SEARCH_API_KEY: str
    SEARCH_INDEX_NAME: str

    # Timeouts (seconds)
    LLM_TIMEOUT: float = 30.0

    # Retrieval
    TOP_K: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


try:
    # pydantic-settings pulls values from environment automatically
    settings = Settings()           # pyright: ignore[reportCallIssue]
except ValidationError as e:
    raise RuntimeError(f"Invalid configuration: {e}") from e


# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
log = logging.getLogger("rag-app")


# ---------------------------------------------------------------------
# App
# ---------------------------------------------------------------------
app = FastAPI(title="Azure RAG Service", version="1.0.0")


# ---------------------------------------------------------------------
# Singletons (reused across requests)
# ---------------------------------------------------------------------
_oai = AzureOpenAI(
    api_key=settings.OPENAI_API_KEY,
    api_version=settings.OPENAI_API_VERSION,
    azure_endpoint=str(settings.OPENAI_API_BASE),  # must include /openai
)

_emb = AzureOpenAIEmbeddings(
    model=settings.EMBEDDING_DEPLOYMENT,
    api_key=settings.OPENAI_API_KEY,               # type: ignore[arg-type]
    api_version=settings.OPENAI_API_VERSION,
    azure_endpoint=str(settings.OPENAI_API_BASE),
)

_vs = AzureSearch(
    azure_search_endpoint=str(settings.SEARCH_SERVICE_NAME),
    azure_search_key=settings.SEARCH_API_KEY,
    index_name=settings.SEARCH_INDEX_NAME,
    embedding_function=_emb.embed_query,
)


# ---------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------
class AskBody(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)


class AskResponse(BaseModel):
    response: str
    request_id: str


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def coerce_content_to_text(resp: Any) -> str:
    """
    OpenAI 1.x: choice.message.content can be str | list[parts] | None.
    Flatten to a plain string.
    """
    if not resp or not getattr(resp, "choices", None):
        return ""
    msg = resp.choices[0].message
    if msg is None:
        return ""
    content = getattr(msg, "content", None)

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: List[str] = []
        for p in content:
            text = getattr(p, "text", None)
            if text is None and isinstance(p, dict):
                text = p.get("text")
            if text:
                parts.append(text)
        return "".join(parts)

    return ""


def build_prompt(query: str, context: str) -> List[ChatCompletionMessageParam]:
    prompt = (
        "You are a helpful RAG assistant. Use ONLY the provided context. "
        "If the answer is not in the context, say you don't know.\n\n"
        f"CONTEXT:\n{context or '(no context found)'}\n\nQUESTION: {query}"
    )
    return [
        {"role": "system", "content": "Answer using only the provided context."},
        {"role": "user", "content": prompt},
    ]


# Bounded retries for transient LLM errors
retry_llm = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIError)),
)


@retry_llm
def llm_answer(query: str, context: str) -> str:
    resp = _oai.chat.completions.create(
        model=settings.CHAT_DEPLOYMENT,
        messages=build_prompt(query, context),
        temperature=0.2,
        max_tokens=800,
        timeout=settings.LLM_TIMEOUT,
    )
    return coerce_content_to_text(resp)


def retrieve_context(q: str) -> str:
    hits = _vs.similarity_search_with_relevance_scores(q, k=settings.TOP_K)
    if not hits:
        return ""
    parts: List[str] = []
    for doc, _score in hits:
        if getattr(doc, "page_content", None):
            parts.append(doc.page_content)
    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------
# Middleware: request id + basic logging
# ---------------------------------------------------------------------
@app.middleware("http")
async def add_request_id_logging(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    try:
        response = await call_next(request)
    except Exception:
        log.exception("unhandled_error request_id=%s path=%s", request_id, request.url.path)
        return JSONResponse(status_code=500, content={"error": "internal_error", "request_id": request_id})
    response.headers["x-request-id"] = request_id
    log.info("%s %s -> %s request_id=%s", request.method, request.url.path, response.status_code, request_id)
    return response


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------
@app.get("/")
def root():
    return RedirectResponse(url="/docs", status_code=301)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    # Settings() validation already guarantees required envs exist
    return {"status": "ready", "missing": []}


@app.post("/ask", response_model=AskResponse)
def ask(body: AskBody):
    # 1) retrieve
    try:
        ctx = retrieve_context(body.query)
    except Exception as e:
        log.exception("search_error")
        raise HTTPException(status_code=502, detail=f"Search error: {e}")

    # 2) answer
    try:
        text = llm_answer(body.query, ctx)
    except RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limited by model provider")
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="LLM timeout")
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"LLM upstream error: {e}") from e
    except Exception:
        log.exception("llm_error")
        raise HTTPException(status_code=500, detail="LLM error")

    return AskResponse(response=text, request_id=str(uuid.uuid4()))


# Prometheus /metrics
Instrumentator().instrument(app).expose(app)
