import json
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "social" / "zalo.json").read_text(encoding="utf-8"))
CREDS = {"app_id": "4318123456", "secret_key": "ZALO-SECRET-abc", "refresh_token": "RT-zalo-1", "author": "Shop News", "cover_photo_url": "https://cdn.example.com/cover.jpg"}
API = "https://openapi.zalo.me"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


@pytest.fixture
def token():
    return respx.post("https://oauth.zaloapp.com/v4/oa/access_token").mock(return_value=httpx.Response(200, json={"access_token": "AT-zalo-1", "refresh_token": "RT-zalo-2", "expires_in": "90000"}))


@pytest.mark.asyncio
@respx.mock
async def test_publish_text_creates_a_normal_article(token):
    route = respx.post(API + "/v2.0/article/create").mock(return_value=httpx.Response(200, json={"error": 0, "message": "Success", "data": {"token": "9xk090B1"}}))
    res = await _server().call_tool("publish_text", {"text": "Khai trương"})
    assert res.is_error is False and res.structured_content["id"] == "9xk090B1"
    body = json.loads(route.calls[0].request.content)
    assert body == {"type": "normal", "title": "Khai trương", "author": "Shop News", "cover": {"cover_type": "photo", "photo_url": "https://cdn.example.com/cover.jpg", "status": "show"},
                    "description": "Khai trương", "body": [{"type": "text", "content": "Khai trương"}], "status": "show", "comment": "show"}
    assert route.calls[0].request.headers["access_token"] == "AT-zalo-1"
    assert token.calls[0].request.headers["secret_key"] == "ZALO-SECRET-abc"


@pytest.mark.asyncio
@respx.mock
async def test_publish_image_uses_images_as_cover_and_paragraphs(token):
    route = respx.post(API + "/v2.0/article/create").mock(return_value=httpx.Response(200, json={"error": 0, "data": {"token": "tk2"}}))
    await _server().call_tool("publish_image", {"text": "New stock", "image_urls": ["https://i.example/a.jpg", "https://i.example/b.jpg"]})
    body = json.loads(route.calls[0].request.content)
    assert body["cover"]["photo_url"] == "https://i.example/a.jpg"
    assert body["body"] == [{"type": "text", "content": "New stock"}, {"type": "image", "url": "https://i.example/a.jpg"}]


@pytest.mark.asyncio
@respx.mock
async def test_delete_and_error(token):
    route = respx.post(API + "/v2.0/article/remove").mock(side_effect=[httpx.Response(200, json={"error": 0, "message": "Success"}), httpx.Response(200, json={"error": -201, "message": "Article not exist"})])
    s = _server()
    ok = await s.call_tool("delete", {"post_id": "39c07ccbe78e0ed0579f"})
    assert ok.structured_content["status"] == "deleted" and json.loads(route.calls[0].request.content) == {"id": "39c07ccbe78e0ed0579f"}
    bad = await s.call_tool("delete", {"post_id": "x"})
    assert bad.is_error is True
