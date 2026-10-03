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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "twitch.json").read_text(encoding="utf-8"))
CREDS = {"client_id": "twcid", "client_secret": "tw-client-secret", "refresh_token": "tw-refresh-1", "sender_id": "123", "broadcaster_id": "999"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _token():
    return respx.post("https://id.twitch.tv/oauth2/token").mock(return_value=httpx.Response(200, json={"access_token": "tw-access-0001", "expires_in": 14000, "refresh_token": "tw-refresh-1", "token_type": "bearer"}))


@pytest.mark.asyncio
async def test_tools_follow_the_messaging_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["me", "reply", "send"]


@pytest.mark.asyncio
@respx.mock
async def test_send_whispers_with_query_ids_and_client_id_header():
    _token()
    route = respx.post(url__startswith="https://api.twitch.tv/helix/whispers").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("send", {"to": "456", "text": "hello"})
    assert res.is_error is False and res.structured_content["status"] == "sent"
    req = route.calls.last.request
    assert req.url.params["from_user_id"] == "123" and req.url.params["to_user_id"] == "456"
    assert json.loads(req.content) == {"message": "hello"}
    assert req.headers["Authorization"] == "Bearer tw-access-0001" and req.headers["Client-Id"] == "twcid"


@pytest.mark.asyncio
@respx.mock
async def test_reply_posts_a_chat_reply_in_the_configured_channel():
    _token()
    route = respx.post("https://api.twitch.tv/helix/chat/messages").mock(return_value=httpx.Response(200, json={"data": [{"message_id": "abc-123", "is_sent": True}]}))
    res = await _server().call_tool("reply", {"thread_id": "parent-1", "text": "thanks"})
    assert res.structured_content["message_id"] == "abc-123"
    assert json.loads(route.calls.last.request.content) == {"broadcaster_id": "999", "sender_id": "123", "message": "thanks", "reply_parent_message_id": "parent-1"}


@pytest.mark.asyncio
@respx.mock
async def test_whisper_rate_limit_and_auth_errors_hide_secrets():
    _token()
    respx.post(url__startswith="https://api.twitch.tv/helix/whispers").mock(return_value=httpx.Response(429, headers={"Retry-After": "5"}, json={"message": "too many"}))
    res = await _server().call_tool("send", {"to": "456", "text": "x"})
    assert res.structured_content["error"] == "rate_limited"
    respx.get("https://api.twitch.tv/helix/users").mock(return_value=httpx.Response(401, json={"message": "invalid token tw-access-0001"}))
    res = await _server().call_tool("me", {})
    dumped = json.dumps(res.structured_content)
    assert res.structured_content["error"] == "auth_error" and "tw-access-0001" not in dumped and "tw-client-secret" not in dumped
