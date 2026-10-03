import json
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "messaging" / "kakao.json").read_text(encoding="utf-8"))
CREDS = {"client_id": "restapikey1", "client_secret": "kakao-client-secret", "refresh_token": "kakao-refresh-token-1", "link_url": "https://shop.example.com"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _token():
    return respx.post("https://kauth.kakao.com/oauth/token").mock(return_value=httpx.Response(200, json={"token_type": "bearer", "access_token": "kakao-access-0001", "expires_in": 43199}))


@pytest.mark.asyncio
async def test_tools_follow_the_messaging_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["me", "send"]


@pytest.mark.asyncio
@respx.mock
async def test_send_posts_a_text_template_to_one_friend_uuid():
    tok = _token()
    route = respx.post("https://kapi.kakao.com/v1/api/talk/friends/message/default/send").mock(return_value=httpx.Response(200, json={"successful_receiver_uuids": ["abcdefg0001"]}))
    res = await _server().call_tool("send", {"to": "abcdefg0001", "text": "Order shipped"})
    assert res.is_error is False and res.structured_content["status"] == "sent"
    t = parse_qs(tok.calls.last.request.content.decode())
    assert t["grant_type"] == ["refresh_token"] and t["client_id"] == ["restapikey1"] and t["refresh_token"] == ["kakao-refresh-token-1"]
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer kakao-access-0001"
    form = parse_qs(req.content.decode())
    assert json.loads(form["receiver_uuids"][0]) == ["abcdefg0001"]
    assert json.loads(form["template_object"][0]) == {"object_type": "text", "text": "Order shipped", "link": {"web_url": "https://shop.example.com", "mobile_web_url": "https://shop.example.com"}}


@pytest.mark.asyncio
@respx.mock
async def test_rotated_refresh_token_replaces_the_old_one():
    respx.post("https://kauth.kakao.com/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "kakao-access-0002", "expires_in": 43199, "refresh_token": "kakao-refresh-token-2", "refresh_token_expires_in": 5184000}))
    respx.get("https://kapi.kakao.com/v2/user/me").mock(return_value=httpx.Response(200, json={"id": 123}))
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test")
    res = await build_server(SPEC, transport=t).call_tool("me", {})
    assert res.is_error is False and t.creds["refresh_token"] == "kakao-refresh-token-2"


@pytest.mark.asyncio
@respx.mock
async def test_refused_refresh_is_an_auth_error_without_secrets():
    respx.post("https://kauth.kakao.com/oauth/token").mock(return_value=httpx.Response(401, json={"error": "invalid_grant", "error_description": "refresh_token=kakao-refresh-token-1 expired"}))
    res = await _server().call_tool("me", {})
    dumped = json.dumps(res.structured_content)
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "kakao-refresh-token-1" not in dumped and "kakao-client-secret" not in dumped
