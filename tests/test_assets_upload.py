import pytest


@pytest.mark.asyncio
async def test_assets_upload_and_access(client, user_headers):
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc``\x00\x00\x00\x04\x00\x01\x0b\xe7\x02\x9b\x00\x00\x00\x00IEND\xaeB`\x82"

    resp = await client.post(
        "/api/assets/upload",
        headers=user_headers,
        files={"file": ("tiny.png", png_bytes, "image/png")},
    )
    assert resp.status_code == 200

    payload = resp.json()
    assert payload["mime_type"] == "image/png"
    assert payload["size_bytes"] == len(png_bytes)
    assert payload["url"].startswith("/uploads/")

    file_resp = await client.get(payload["url"])
    assert file_resp.status_code == 200
    assert file_resp.content == png_bytes
