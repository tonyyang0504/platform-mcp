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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "postmark.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"server_token": "srv-tok", "sender": "sender@example.com"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_messaging_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["list_inbound", "me", "send"]
    send = next(t for t in tools if t.name == "send")
    assert send.annotations.read_only_hint is False and send.meta["platform_mcp/endpoint"] == "/email"
    assert set(SPEC["adapter"]["not_offered"]) == {"reply", "get_thread", "mark_read"}


@pytest.mark.asyncio
@respx.mock
async def test_send_fills_from_with_the_sender_config_field_and_the_server_token_header():
    route = respx.post("https://api.postmarkapp.com/email").mock(return_value=httpx.Response(200, json={
        "To": "receiver@example.com", "SubmittedAt": "2014-02-17T07:25:01.4178645-05:00", "MessageID": "0a129aee-e1cd-480d-b08d-4f48548ff48d", "ErrorCode": 0, "Message": "OK"}))
    res = await _server().call_tool("send", {"to": "receiver@example.com", "subject": "Hello", "text": "hi", "channel": "outbound"})
    assert res.is_error is False
    assert res.structured_content["message_id"] == "0a129aee-e1cd-480d-b08d-4f48548ff48d" and res.structured_content["status"] == "OK"
    body = json.loads(route.calls.last.request.content)
    assert body == {"From": "sender@example.com", "To": "receiver@example.com", "Subject": "Hello", "TextBody": "hi", "MessageStream": "outbound"}
    assert route.calls.last.request.headers["X-Postmark-Server-Token"] == "srv-tok"


@pytest.mark.asyncio
@respx.mock
async def test_list_inbound_uses_count_and_offset():
    respx.get("https://api.postmarkapp.com/messages/inbound").mock(return_value=httpx.Response(200, json={
        "TotalCount": 1, "InboundMessages": [{"From": "sender@example.com", "FromName": "Sender", "To": "inbound@example.com", "Subject": "Test", "Date": "Wed, 12 Dec 2012 10:15:12 -0500", "MessageID": "4d9ea3c1-e0a2-4b75-b3b3-f1dec8c5b23a", "Status": "Processed"}]}))
    res = await _server().call_tool("list_inbound", {"page": 2, "limit": 10})
    assert res.is_error is False
    m = res.structured_content["messages"][0]
    assert m["id"] == "4d9ea3c1-e0a2-4b75-b3b3-f1dec8c5b23a" and m["from"] == "sender@example.com" and m["to"] == "inbound@example.com"
    assert res.structured_content["total"] == 1 and res.structured_content["next_page"] is None
    req = respx.calls.last.request
    assert req.url.params["count"] == "10" and req.url.params["offset"] == "10"


@pytest.mark.asyncio
@respx.mock
async def test_unauthorized_is_an_auth_error_result():
    respx.get("https://api.postmarkapp.com/server").mock(return_value=httpx.Response(401, json={"ErrorCode": 10, "Message": "No Account or Server API tokens were supplied in the HTTP headers."}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
