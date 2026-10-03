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

SPEC = json.loads((ROOT / "catalog" / "social" / "line.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"channel_access_token": "line-social-secret"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_social_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "me", "publish_image", "publish_text"]
    pt = next(t for t in tools if t.name == "publish_text")
    assert pt.annotations.read_only_hint is False and pt.meta["platform_mcp/endpoint"] == "/v2/bot/message/broadcast"
    assert "EVERY FRIEND" in pt.description


@pytest.mark.asyncio
@respx.mock
async def test_publish_text_broadcasts_one_text_message_with_the_bearer_token():
    route = respx.post("https://api.line.me/v2/bot/message/broadcast").mock(return_value=httpx.Response(200, json={}))
    res = await _server().call_tool("publish_text", {"text": "Hello friends", "reply_to": "x"})
    assert res.is_error is False and res.structured_content["id"] == "broadcast"
    req = route.calls.last.request
    assert json.loads(req.content) == {"messages": [{"type": "text", "text": "Hello friends"}]}
    assert req.headers["Authorization"] == "Bearer line-social-secret"


@pytest.mark.asyncio
@respx.mock
async def test_publish_image_sends_an_image_message_from_the_first_url():
    route = respx.post("https://api.line.me/v2/bot/message/broadcast").mock(return_value=httpx.Response(200, json={}))
    res = await _server().call_tool("publish_image", {"image_urls": ["https://example.com/a.jpg", "https://example.com/b.jpg"], "text": "t"})
    assert res.is_error is False
    assert json.loads(route.calls.last.request.content) == {"messages": [{"type": "image", "originalContentUrl": "https://example.com/a.jpg", "previewImageUrl": "https://example.com/a.jpg"}]}


@pytest.mark.asyncio
@respx.mock
async def test_analytics_post_reads_message_event_by_request_id():
    route = respx.get("https://api.line.me/v2/bot/insight/message/event").mock(return_value=httpx.Response(200, json={
        "overview": {"requestId": "f70dd685-499a-4231-a441-f24b8d4fba21", "timestamp": 1568214000, "delivered": 320, "uniqueImpression": 82, "uniqueClick": 51},
        "messages": [{"seq": 1, "impression": 136}], "clicks": []}))
    res = await _server().call_tool("analytics_post", {"post_id": "f70dd685-499a-4231-a441-f24b8d4fba21"})
    sc = res.structured_content
    assert res.is_error is False and sc["post_id"] == "f70dd685-499a-4231-a441-f24b8d4fba21" and sc["delivered"] == 320 and sc["unique_click"] == 51
    assert route.calls.last.request.url.params["requestId"] == "f70dd685-499a-4231-a441-f24b8d4fba21"


@pytest.mark.asyncio
@respx.mock
async def test_invalid_token_is_an_auth_error_without_the_secret():
    respx.get("https://api.line.me/v2/bot/info").mock(return_value=httpx.Response(401, json={"message": "Authentication failed. token=line-social-secret"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "line-social-secret" not in json.dumps(res.structured_content)
