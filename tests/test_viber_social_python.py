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

SPEC = json.loads((ROOT / "catalog" / "social" / "viber.json").read_text(encoding="utf-8"))


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], {"auth_token": "viber-channel-secret", "sender_id": "01234567890A="}, 50, "test", envelope=a["envelope"])
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_social_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["me", "publish_image", "publish_text"]
    assert next(t for t in tools if t.name == "publish_text").meta["platform_mcp/endpoint"] == "/post"


@pytest.mark.asyncio
@respx.mock
async def test_publish_text_posts_with_token_and_superadmin_in_the_body():
    route = respx.post("https://chatapi.viber.com/pa/post").mock(return_value=httpx.Response(200, json={"status": 0, "status_message": "ok", "message_token": 5741311803571721087}))
    res = await _server().call_tool("publish_text", {"text": "Hello world!"})
    assert res.is_error is False and res.structured_content["id"] == "5741311803571721087"
    assert json.loads(route.calls.last.request.content) == {"auth_token": "viber-channel-secret", "from": "01234567890A=", "type": "text", "text": "Hello world!"}


@pytest.mark.asyncio
@respx.mock
async def test_publish_image_sends_a_picture_message():
    route = respx.post("https://chatapi.viber.com/pa/post").mock(return_value=httpx.Response(200, json={"status": 0, "status_message": "ok", "message_token": 1}))
    await _server().call_tool("publish_image", {"image_urls": ["https://example.com/a.jpeg"], "text": "desc"})
    body = json.loads(route.calls.last.request.content)
    assert body["type"] == "picture" and body["media"] == "https://example.com/a.jpeg" and body["text"] == "desc"


@pytest.mark.asyncio
@respx.mock
async def test_nonzero_status_is_an_error_without_the_token():
    respx.post("https://chatapi.viber.com/pa/get_account_info").mock(return_value=httpx.Response(200, json={"status": 2, "status_message": "invalidAuthToken viber-channel-secret"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "viber-channel-secret" not in json.dumps(res.structured_content)
