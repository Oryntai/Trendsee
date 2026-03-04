import pytest


@pytest.mark.asyncio
async def test_trends_filters_active_and_type(client):
    response = await client.get("/api/trends", params={"active": "true", "type": "video"})
    assert response.status_code == 200
    data = response.json()

    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    for row in data["items"]:
        assert row["is_active"] is True
        assert row["type"] == "video"


@pytest.mark.asyncio
async def test_trends_sort_cheapest(client):
    response = await client.get("/api/trends", params={"sort": "cheapest"})
    assert response.status_code == 200

    prices = [row["price_tokens"] for row in response.json()["items"]]
    assert prices == sorted(prices)
