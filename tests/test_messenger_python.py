"""Messenger Platform: Page token, conversations inbox, Send API, mark_seen."""
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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "messenger.json").read_text(encoding="utf-8"))
G = "https://graph.facebook.com/v26.0"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"page_access_token": "PAGE-TOKEN", "page_id": "1234"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_and_reply_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_thread", "list_inbound", "mark_read", "me", "send"]
    assert set(SPEC["adapter"]["not_offered"]) == {"reply"}


@pytest.mark.asyncio
@respx.mock
async def test_send_uses_the_send_api_shape():
    # developers.facebook.com/docs/messenger-platform/send-messages -> {recipient_id, message_id}
    route = respx.post(f"{G}/1234/messages").mock(return_value=httpx.Response(200, json={"recipient_id": "PSID1", "message_id": "m_AG5Hz2U"}))
    res = await _server().call_tool("send", {"to": "PSID1", "text": "Hello, world!"})
    assert res.is_error is False and res.structured_content["message_id"] == "m_AG5Hz2U" and res.structured_content["status"] == "sent"
    req = route.calls.last.request
    assert json.loads(req.content) == {"recipient": {"id": "PSID1"}, "messaging_type": "RESPONSE", "message": {"text": "Hello, world!"}}
    assert req.headers["Authorization"] == "Bearer PAGE-TOKEN"


@pytest.mark.asyncio
@respx.mock
async def test_list_inbound_maps_latest_message_per_conversation_and_drops_empty_ones():
    respx.get(f"{G}/1234/conversations").mock(return_value=httpx.Response(200, json={"data": [
        {"id": "t_1", "updated_time": "2026-09-24T10:00:00+0000", "messages": {"data": [{"id": "m_1", "message": "hi page", "from": {"name": "Ann", "id": "PSID1"}, "created_time": "2026-09-24T10:00:00+0000"}]}},
        {"id": "t_2", "updated_time": "2026-09-20T10:00:00+0000"}]}))
    res = await _server().call_tool("list_inbound", {})
    msgs = res.structured_content["messages"]
    assert len(msgs) == 1 and msgs[0]["id"] == "m_1" and msgs[0]["thread_id"] == "t_1" and msgs[0]["from"] == "Ann" and msgs[0]["from_id"] == "PSID1" and msgs[0]["text"] == "hi page"
    params = respx.calls.last.request.url.params
    assert params["platform"] == "messenger" and params["fields"].startswith("id,updated_time,messages.limit(1)")


@pytest.mark.asyncio
@respx.mock
async def test_get_thread_reads_conversation_messages_capped_at_20():
    respx.get(f"{G}/t_1/messages").mock(return_value=httpx.Response(200, json={"data": [
        {"id": "m_2", "message": "reply", "from": {"name": "Shop", "id": "1234"}, "to": {"data": [{"name": "Ann", "id": "PSID1"}]}, "created_time": "2026-09-24T10:01:00+0000"}]}))
    res = await _server().call_tool("get_thread", {"thread_id": "t_1", "limit": 50})
    m = res.structured_content["messages"][0]
    assert m["id"] == "m_2" and m["from"] == "Shop" and m["to"] == "Ann" and m["text"] == "reply"
    assert respx.calls.last.request.url.params["limit"] == "20"


@pytest.mark.asyncio
@respx.mock
async def test_mark_read_sends_mark_seen_and_permission_error_is_auth_error():
    route = respx.post(f"{G}/1234/messages").mock(return_value=httpx.Response(200, json={"recipient_id": "PSID1"}))
    res = await _server().call_tool("mark_read", {"thread_id": "PSID1"})
    assert res.is_error is False and res.structured_content["status"] == "ok"
    assert json.loads(route.calls.last.request.content) == {"recipient": {"id": "PSID1"}, "sender_action": "mark_seen"}
    respx.get(f"{G}/1234").mock(return_value=httpx.Response(403, json={"error": {"message": "(#200) Permissions error", "code": 200}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
