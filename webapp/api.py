
"""
Defines API routes for the FastAPI app.
`app` is imported from main.py so that routes and middlewares are centralized.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import APIError, RateLimitError, APITimeoutError
from webapp.services import rag

router = APIRouter()


class AskBody(BaseModel):
    query: str


class AskResponse(BaseModel):
    response: str
    request_id: str


@router.get("/healthz")
def healthz():
    return {"status": "ok"}


@router.get("/readyz")
def readyz():
    return {"status": "ready", "missing": []}


@router.post("/ask", response_model=AskResponse)
def ask(body: AskBody):
    try:
        ctx = rag.retrieve(body.query)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Search error: {e}")

    try:
        text = rag.answer(body.query, ctx)
    except RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limited by model provider")
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="LLM timeout")
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"LLM upstream error: {e}")
    except Exception:
        raise HTTPException(status_code=500, detail="LLM error")

    import uuid
    return AskResponse(response=text, request_id=str(uuid.uuid4()))
