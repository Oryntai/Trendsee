import pytest


@pytest.mark.asyncio
async def test_generation_reaches_done_and_has_result(client, user_headers):
    trends_resp = await client.get("/api/trends")
    trend_id = trends_resp.json()["items"][0]["id"]

    create_resp = await client.post(
        "/api/generations",
        headers={**user_headers, "Idempotency-Key": "33333333-3333-3333-3333-333333333333"},
        json={
            "trend_id": trend_id,
            "prompt": "Create a concise but vivid concept",
            "resources": [],
            "asset_ids": [],
        },
    )
    assert create_resp.status_code == 201
    generation_id = create_resp.json()["id"]

    details_resp = await client.get(f"/api/generations/{generation_id}", headers=user_headers)
    assert details_resp.status_code == 200
    details = details_resp.json()

    assert details["status"] == "done"
    assert details["provider"] == "mock"
    assert isinstance(details["result_text"], str)
    assert len(details["result_text"].strip()) > 0


@pytest.mark.asyncio
async def test_generation_events_stream_done(client, user_headers):
    trends_resp = await client.get("/api/trends")
    trend_id = trends_resp.json()["items"][0]["id"]

    create_resp = await client.post(
        "/api/generations",
        headers={**user_headers, "Idempotency-Key": "44444444-4444-4444-4444-444444444444"},
        json={
            "trend_id": trend_id,
            "prompt": "Generate status stream test",
            "resources": [],
            "asset_ids": [],
        },
    )
    assert create_resp.status_code == 201
    generation_id = create_resp.json()["id"]

    events_resp = await client.get(
        f"/api/generations/{generation_id}/events",
        headers=user_headers,
    )
    assert events_resp.status_code == 200
    assert events_resp.headers["content-type"].startswith("text/event-stream")
    assert '"status": "done"' in events_resp.text
