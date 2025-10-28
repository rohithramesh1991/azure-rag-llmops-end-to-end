from __future__ import annotations

from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import APIError, RateLimitError, APITimeoutError
from openai.types.chat import ChatCompletionMessageParam

from webapp.config import settings
from webapp.clients import get_oai_client, get_vectorstore

# NEW: Prometheus metrics
from webapp.metrics import LLMCallTimer

class RateLimited(Exception): ...
class TimedOut(Exception): ...
class UpstreamError(Exception): ...

def _prompt(query: str, context: str) -> List[ChatCompletionMessageParam]:
    return [
        {"role": "system", "content": "Answer using only the provided context."},
        {
            "role": "user",
            "content": (
                "You are a helpful RAG assistant. Use ONLY the provided context. "
                "If the answer is not in the context, say you don't know.\n\n"
                f"CONTEXT:\n{context or '(no context found)'}\n\nQUESTION: {query}"
            ),
        },
    ]

def retrieve(q: str) -> str:
    vs = get_vectorstore()
    hits = vs.similarity_search_with_relevance_scores(q, k=settings.TOP_K)
    if not hits:
        return ""
    parts: list[str] = []
    for doc, _ in hits:
        if getattr(doc, "page_content", None):
            parts.append(doc.page_content)
    return "\n\n---\n\n".join(parts)

_retry_llm = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIError)),
)

def _coerce_content(resp) -> str:
    if not resp or not getattr(resp, "choices", None):
        return ""
    msg = resp.choices[0].message
    content = getattr(msg, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for p in content:
            text = getattr(p, "text", None)
            if text is None and isinstance(p, dict):
                text = p.get("text")
            if text:
                parts.append(text)
        return "".join(parts)
    return ""

def _usage(resp) -> tuple[int, int]:
    usage = getattr(resp, "usage", None) or {}
    try:
        pt = int(getattr(usage, "prompt_tokens", 0) or usage.get("prompt_tokens", 0) or 0)
        ct = int(getattr(usage, "completion_tokens", 0) or usage.get("completion_tokens", 0) or 0)
    except Exception:
        pt, ct = 0, 0
    return pt, ct

@_retry_llm
def answer(query: str, context: str) -> str:
    oai = get_oai_client()

    # Emit LLM metrics around the call
    provider = "azure_openai"
    model = settings.CHAT_DEPLOYMENT
    with LLMCallTimer(provider=provider, model=model) as t:
        try:
            resp = oai.chat.completions.create(
                model=model,
                messages=_prompt(query, context),
                temperature=0.2,
                max_tokens=800,
                timeout=settings.LLM_TIMEOUT,
            )
            text = _coerce_content(resp)
            pt, ct = _usage(resp)
            t.record_success(prompt_tokens=pt, completion_tokens=ct, cost_usd=0.0)
            return text

        except RateLimitError as e:
            t.record_error("RateLimitError"); raise RateLimited() from e
        except APITimeoutError as e:
            t.record_error("APITimeoutError"); raise TimedOut() from e
        except APIError as e:
            t.record_error("APIError"); raise UpstreamError(str(e)) from e
        except Exception as e:
            t.record_error(e.__class__.__name__); raise
