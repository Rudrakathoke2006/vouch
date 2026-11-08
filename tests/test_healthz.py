import pytest
from httpx import AsyncClient, ASGITransport
from api.src.main import app


@pytest.mark.asyncio
async def test_healthz_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "vouch-api"
        assert "payment_provider" in data
        assert "llm_provider" in data
