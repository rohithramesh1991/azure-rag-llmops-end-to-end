
from __future__ import annotations

from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import APIError, RateLimitError, APITimeoutError
from openai.types.chat import ChatCompletionMessageParam

from webapp.config import settings
from webapp.clients import get_oai_client, get_vectorstore

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

@_retry_llm
def answer(query: str, context: str) -> str:
    oai = get_oai_client()
    try:
        resp = oai.chat.completions.create(
            model=settings.CHAT_DEPLOYMENT,
            messages=_prompt(query, context),
            temperature=0.2,
            max_tokens=800,
            timeout=settings.LLM_TIMEOUT,
        )
    except RateLimitError as e:
        raise RateLimited() from e
    except APITimeoutError as e:
        raise TimedOut() from e
    except APIError as e:
        raise UpstreamError(str(e)) from e

    return _coerce_content(resp)
