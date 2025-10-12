# test/test_health.py
import pytest
from httpx import AsyncClient, ASGITransport
from webapp.main import app

@pytest.mark.asyncio
async def test_healthz():
    transport = ASGITransport(app=app)         # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_readyz():
    transport = ASGITransport(app=app)         # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/readyz")
    assert r.status_code == 200
    assert "status" in r.json()
