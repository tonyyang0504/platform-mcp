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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "microsoft_graph.json").read_text(encoding="utf-8"))
M = "https://graph.microsoft.com/v1.0"
TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"client_id": "app", "client_secret": "sec", "refresh_token": "0.AR"}, 50, "test"))


def _token():
    return respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "eyJ.M", "expires_in": 3600, "refresh_token": "0.AR2"}))


@pytest.mark.asyncio
async def test_all_messaging_verbs_are_served():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_thread", "list_inbound", "mark_read", "me", "reply", "send"]


@pytest.mark.asyncio
@respx.mock
async def test_send_mail_json_body_and_202():
    tok = _token()
    route = respx.post(f"{M}/me/sendMail").mock(return_value=httpx.Response(202))
    res = await _server().call_tool("send", {"to": "fran@contoso.com", "text": "Lunch?", "subject": "Hi"})
    assert res.is_error is False and res.structured_content["status"] == "sent"
    assert json.loads(route.calls.last.request.content) == {"message": {"subject": "Hi", "body": {"contentType": "Text", "content": "Lunch?"}, "toRecipients": [{"emailAddress": {"address": "fran@contoso.com"}}]}}
    form = dict(x.split("=", 1) for x in tok.calls[0].request.content.decode().split("&"))
    assert form["grant_type"] == "refresh_token" and form["client_id"] == "app"


@pytest.mark.asyncio
@respx.mock
async def test_list_inbound_keeps_odata_dollar_params():
    _token()
    respx.get(url__startswith=f"{M}/me/mailFolders/inbox/messages").mock(return_value=httpx.Response(200, json={"value": [
        {"id": "AAMk1", "conversationId": "c1", "from": {"emailAddress": {"address": "a@b.c"}}, "bodyPreview": "hey", "receivedDateTime": "2026-09-24T09:00:00Z"}]}))
    res = await _server().call_tool("list_inbound", {"limit": 5})
    m = res.structured_content["messages"][0]
    assert m["from"] == "a@b.c" and m["thread_id"] == "c1" and m["text"] == "hey"
    assert "$top=5" in str(respx.calls.last.request.url)


@pytest.mark.asyncio
@respx.mock
async def test_get_thread_filter_reply_and_mark_read():
    _token()
    respx.get(url__startswith=f"{M}/me/messages?").mock(return_value=httpx.Response(200, json={"value": []}))
    await _server().call_tool("get_thread", {"thread_id": "c1"})
    assert respx.calls.last.request.url.params["$filter"] == "conversationId eq 'c1'"
    reply = respx.post(f"{M}/me/messages/AAMk1/reply").mock(return_value=httpx.Response(202))
    res = await _server().call_tool("reply", {"thread_id": "AAMk1", "text": "sure"})
    assert res.structured_content["status"] == "sent" and json.loads(reply.calls.last.request.content) == {"comment": "sure"}
    patch = respx.patch(f"{M}/me/messages/AAMk1").mock(return_value=httpx.Response(200, json={"id": "AAMk1", "isRead": True}))
    res = await _server().call_tool("mark_read", {"message_id": "AAMk1"})
    assert res.structured_content["status"] == "read" and json.loads(patch.calls.last.request.content) == {"isRead": True}
