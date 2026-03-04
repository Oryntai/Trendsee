import pytest


@pytest.mark.asyncio
async def test_idempotent_generation_charge_once(client, user_headers):
    trends_resp = await client.get("/api/trends")
    trend_id = trends_resp.json()["items"][0]["id"]

    me_before = await client.get("/api/me", headers=user_headers)
    balance_before = me_before.json()["token_balance"]

    idem_key = "11111111-1111-1111-1111-111111111111"
    payload = {
        "trend_id": trend_id,
        "prompt": "make it bold and concise",
        "resources": [{"url": "https://example.com/ref", "note": "ref"}],
        "asset_ids": [],
    }

    first = await client.post(
        "/api/generations",
        headers={**user_headers, "Idempotency-Key": idem_key},
        json=payload,
    )
    assert first.status_code == 201
    first_data = first.json()

    second = await client.post(
        "/api/generations",
        headers={**user_headers, "Idempotency-Key": idem_key},
        json=payload,
    )
    assert second.status_code == 200
    second_data = second.json()

    assert first_data["id"] == second_data["id"]

    me_after = await client.get("/api/me", headers=user_headers)
    balance_after = me_after.json()["token_balance"]
    assert balance_after == first_data["balance_after"]
    assert balance_after < balance_before


@pytest.mark.asyncio
async def test_idempotent_generation_conflict_on_different_payload(client, user_headers):
    trends_resp = await client.get("/api/trends")
    trend_id = trends_resp.json()["items"][0]["id"]

    idem_key = "22222222-2222-2222-2222-222222222222"

    first = await client.post(
        "/api/generations",
        headers={**user_headers, "Idempotency-Key": idem_key},
        json={
            "trend_id": trend_id,
            "prompt": "first prompt",
            "resources": [],
            "asset_ids": [],
        },
    )
    assert first.status_code in (200, 201)

    second = await client.post(
        "/api/generations",
        headers={**user_headers, "Idempotency-Key": idem_key},
        json={
            "trend_id": trend_id,
            "prompt": "different prompt",
            "resources": [],
            "asset_ids": [],
        },
    )
    assert second.status_code == 409
