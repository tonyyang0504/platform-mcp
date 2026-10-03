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

SPEC = json.loads((ROOT / "catalog" / "social" / "twitch.json").read_text(encoding="utf-8"))
H = "https://api.twitch.tv/helix"


def _server():
    a = SPEC["adapter"]
    creds = {"client_id": "wbmy", "client_secret": "sec", "refresh_token": "eyJr", "broadcaster_id": "12826", "sender_id": "141981764"}
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], creds, 50, "test"))


def _token():
    return respx.post("https://id.twitch.tv/oauth2/token").mock(return_value=httpx.Response(200, json={"access_token": "2gbd", "expires_in": 15583, "refresh_token": "eyJr2"}))


@pytest.mark.asyncio
async def test_tools():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["delete", "me", "publish_text", "reply_comment"]


@pytest.mark.asyncio
@respx.mock
async def test_chat_message_with_client_id_header():
    _token()
    route = respx.post(f"{H}/chat/messages").mock(return_value=httpx.Response(200, json={"data": [{"message_id": "abc-123", "is_sent": True}]}))
    res = await _server().call_tool("publish_text", {"text": "Hello chat"})
    assert res.structured_content["id"] == "abc-123"
    req = route.calls.last.request
    assert json.loads(req.content) == {"broadcaster_id": "12826", "sender_id": "141981764", "message": "Hello chat"}
    assert req.headers["Client-Id"] == "wbmy" and req.headers["Authorization"] == "Bearer 2gbd"


@pytest.mark.asyncio
@respx.mock
async def test_reply_sets_parent_and_delete_always_names_one_message():
    _token()
    route = respx.post(f"{H}/chat/messages").mock(return_value=httpx.Response(200, json={"data": [{"message_id": "def", "is_sent": True}]}))
    await _server().call_tool("reply_comment", {"comment_id": "abc-123", "text": "hi"})
    assert json.loads(route.calls.last.request.content)["reply_parent_message_id"] == "abc-123"
    d = respx.delete(url__startswith=f"{H}/moderation/chat").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("delete", {"post_id": "abc-123"})
    assert res.structured_content["status"] == "deleted"
    q = d.calls.last.request.url.params
    assert q["message_id"] == "abc-123" and q["broadcaster_id"] == "12826" and q["moderator_id"] == "141981764"
    res = await _server().call_tool("delete", {"post_id": ""})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and d.call_count == 1
