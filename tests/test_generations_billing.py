import pytest


@pytest.mark.asyncio
async def test_insufficient_tokens_returns_402(client, user_headers, admin_headers):
    trends_resp = await client.get("/api/trends")
    trend_id = trends_resp.json()["items"][0]["id"]

    me_before = await client.get("/api/me", headers=user_headers)
    balance_before = me_before.json()["token_balance"]

    patch_resp = await client.patch(
        f"/api/trends/{trend_id}",
        headers=admin_headers,
        json={"price_tokens": balance_before + 1},
    )
    assert patch_resp.status_code == 200

    create_resp = await client.post(
        "/api/generations",
        headers=user_headers,
        json={
            "trend_id": trend_id,
            "prompt": "make a script",
            "resources": [],
            "asset_ids": [],
        },
    )
    assert create_resp.status_code == 402

    me_after = await client.get("/api/me", headers=user_headers)
    assert me_after.json()["token_balance"] == balance_before
