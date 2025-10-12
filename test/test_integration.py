# test/test_integration.py
import pytest
from httpx import AsyncClient, ASGITransport
from webapp import main

@pytest.mark.asyncio
async def test_ask_endpoint(monkeypatch):
    # Replace retrieval and LLM layers so the endpoint is deterministic
    monkeypatch.setattr(main, "retrieve_context", lambda q: "context")
    monkeypatch.setattr(main, "llm_answer", lambda q, c: "final-answer")
    
    transport = ASGITransport(app=main.app)      # type: ignore[arg-type]

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/ask", json={"query": "hello"})
    assert r.status_code == 200
    assert r.json()["response"] == "final-answer"
