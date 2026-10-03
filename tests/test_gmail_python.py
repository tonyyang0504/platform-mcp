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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "gmail.json").read_text(encoding="utf-8"))
G = "https://gmail.googleapis.com/gmail/v1"
CREDS = {"client_id": "cid.apps.googleusercontent.com", "client_secret": "GOCSPX-sec", "refresh_token": "1//refresh"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _token():
    return respx.post("https://oauth2.googleapis.com/token").mock(return_value=httpx.Response(200, json={"access_token": "ya29.A", "expires_in": 3599, "token_type": "Bearer"}))


@pytest.mark.asyncio
async def test_tools_and_not_offered_send():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_thread", "list_inbound", "mark_read", "me"]
    assert "raw" in SPEC["adapter"]["not_offered"]["send"]


@pytest.mark.asyncio
@respx.mock
async def test_refresh_grant_in_body_then_profile():
    tok = _token()
    respx.get(f"{G}/users/me/profile").mock(return_value=httpx.Response(200, json={"emailAddress": "a@example.com", "messagesTotal": 3}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["emailAddress"] == "a@example.com"
    form = dict(x.split("=", 1) for x in tok.calls[0].request.content.decode().split("&"))
    assert form["grant_type"] == "refresh_token" and form["client_secret"] == "GOCSPX-sec" and "Authorization" not in tok.calls[0].request.headers
    assert respx.calls.last.request.headers["Authorization"] == "Bearer ya29.A"


@pytest.mark.asyncio
@respx.mock
async def test_list_inbound_and_thread():
    _token()
    respx.get(f"{G}/users/me/messages").mock(return_value=httpx.Response(200, json={"messages": [{"id": "m1", "threadId": "t1"}], "resultSizeEstimate": 1}))
    res = await _server().call_tool("list_inbound", {"limit": 10})
    assert res.structured_content["messages"][0]["thread_id"] == "t1" and res.structured_content["total"] == 1
    q = respx.calls.last.request.url.params
    assert q["labelIds"] == "INBOX" and q["maxResults"] == "10"
    respx.get(f"{G}/users/me/threads/t1").mock(return_value=httpx.Response(200, json={"id": "t1", "messages": [{"id": "m1", "threadId": "t1", "snippet": "hello", "internalDate": "1700000000000"}]}))
    res = await _server().call_tool("get_thread", {"thread_id": "t1"})
    m = res.structured_content["messages"][0]
    assert m["text"] == "hello" and m["sent_at"] == "1700000000000"
    assert respx.calls.last.request.url.params["format"] == "metadata"


@pytest.mark.asyncio
@respx.mock
async def test_mark_read_removes_unread_label():
    _token()
    route = respx.post(f"{G}/users/me/messages/m1/modify").mock(return_value=httpx.Response(200, json={"id": "m1", "labelIds": ["INBOX"]}))
    res = await _server().call_tool("mark_read", {"message_id": "m1"})
    assert res.is_error is False and res.structured_content["status"] == "read"
    assert json.loads(route.calls.last.request.content) == {"removeLabelIds": ["UNREAD"]}
