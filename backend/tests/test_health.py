from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_health_returns_ok_with_db(client):
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_connect = AsyncMock()
    mock_connect.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_connect.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.routers.health.engine") as mock_engine:
        mock_engine.connect.return_value = mock_connect
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_health_returns_degraded_when_db_unavailable(client):
    with patch("app.api.routers.health.engine") as mock_engine:
        mock_engine.connect.side_effect = ConnectionRefusedError("DB down")
        response = await client.get("/health")


    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"] == "unavailable"
