import pytest
from httpx import AsyncClient, ASGITransport
from webapp.main import app
from webapp.services import rag

@pytest.mark.asyncio
async def test_ask_endpoint(monkeypatch):
    # Stub the service layer
    monkeypatch.setattr(rag, "retrieve", lambda q: "context")
    monkeypatch.setattr(rag, "answer",   lambda q, c: "final-answer")

    transport = ASGITransport(app=app)         # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/ask", json={"query": "hello"})
    assert r.status_code == 200
    assert r.json()["response"] == "final-answer"
