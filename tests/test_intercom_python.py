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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "intercom.json").read_text(encoding="utf-8"))


def _server():
    # admin_id is a non-secret per-install config field (the authoring admin for replies / messages)
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"access_token": "dG9rZW4-secret", "admin_id": "991267386"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_messaging_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_thread", "list_inbound", "mark_read", "me", "reply", "send"]
    reply = next(t for t in tools if t.name == "reply")
    assert reply.annotations.read_only_hint is False and reply.annotations.destructive_hint is False
    assert reply.input_schema["required"] == ["thread_id", "text"]
    assert reply.meta["platform_mcp/endpoint"] == "/conversations/{thread_id}/reply"
    gt = next(t for t in tools if t.name == "get_thread")
    assert gt.annotations.read_only_hint is True and gt.output_schema["required"] == ["messages"]
    assert SPEC["adapter"]["not_offered"] == {}


@pytest.mark.asyncio
@respx.mock
async def test_send_creates_an_admin_in_app_message_with_a_bearer_token():
    # developers.intercom.com .../messages/createmessage -> Message {type, id, created_at, body, message_type, conversation_id}
    route = respx.post("https://api.intercom.io/messages").mock(return_value=httpx.Response(200, json={
        "type": "admin_message", "id": "403918396", "created_at": 1734537780, "body": "heyy", "message_type": "inapp", "conversation_id": "613"}))
    res = await _server().call_tool("send", {"to": "6762f2341bb69f9f2193bc17", "text": "heyy", "subject": "ignored", "channel": "ignored"})
    assert res.is_error is False
    assert res.structured_content["message_id"] == "403918396" and res.structured_content["status"] == "sent"
    body = json.loads(route.calls.last.request.content)
    assert body == {"message_type": "in_app", "body": "heyy", "from": {"type": "admin", "id": "991267386"}, "to": {"type": "user", "id": "6762f2341bb69f9f2193bc17"}}
    assert route.calls.last.request.headers["Authorization"] == "Bearer dG9rZW4-secret"


@pytest.mark.asyncio
@respx.mock
async def test_reply_posts_an_admin_comment():
    route = respx.post("https://api.intercom.io/conversations/123/reply").mock(return_value=httpx.Response(200, json={
        "type": "conversation", "id": "123", "state": "open", "conversation_parts": {"type": "conversation_part.list", "conversation_parts": [{"type": "conversation_part", "id": "3", "part_type": "comment", "body": "<p>Thanks</p>"}], "total_count": 1}}))
    res = await _server().call_tool("reply", {"thread_id": "123", "text": "Thanks"})
    assert res.is_error is False and res.structured_content["status"] == "sent" and "message_id" not in res.structured_content
    assert json.loads(route.calls.last.request.content) == {"message_type": "comment", "type": "admin", "admin_id": "991267386", "body": "Thanks"}


@pytest.mark.asyncio
@respx.mock
async def test_list_inbound_and_get_thread_map_conversations_and_parts():
    respx.get("https://api.intercom.io/conversations").mock(return_value=httpx.Response(200, json={
        "type": "conversation.list", "pages": {"type": "pages", "page": 1, "per_page": 10, "total_pages": 1}, "total_count": 1,
        "conversations": [{"type": "conversation", "id": "471", "created_at": 1734537460, "updated_at": 1734537460, "state": "open", "read": False,
                           "source": {"type": "conversation", "id": "403918320", "body": "<p>this is the message body</p>", "author": {"type": "user", "id": "6762f2341bb69f9f2193bc17", "name": "Joe", "email": "joe@example.com"}}}]}))
    res = await _server().call_tool("list_inbound", {"limit": 10})
    assert res.is_error is False
    m = res.structured_content["messages"][0]
    assert m["id"] == "471" and m["thread_id"] == "471" and m["from"] == "joe@example.com" and m["text"] == "<p>this is the message body</p>"
    assert respx.calls.last.request.url.params["per_page"] == "10"

    respx.get("https://api.intercom.io/conversations/471").mock(return_value=httpx.Response(200, json={
        "type": "conversation", "id": "471", "source": {"body": "first"},
        "conversation_parts": {"type": "conversation_part.list", "total_count": 1, "conversation_parts": [
            {"type": "conversation_part", "id": "3", "part_type": "comment", "body": "Okay!", "created_at": 1663597223, "author": {"type": "admin", "id": "991267386", "name": "Admin", "email": "admin@example.com"}}]}}))
    res = await _server().call_tool("get_thread", {"thread_id": "471"})
    assert res.is_error is False
    p = res.structured_content["messages"][0]
    assert p["id"] == "3" and p["from"] == "admin@example.com" and p["text"] == "Okay!" and p["raw"]["part_type"] == "comment"
    assert res.structured_content["total"] == 1
    assert respx.calls.last.request.url.params["display_as"] == "plaintext"


@pytest.mark.asyncio
@respx.mock
async def test_unauthorized_is_an_auth_error_without_the_token():
    respx.get("https://api.intercom.io/me").mock(return_value=httpx.Response(401, json={
        "type": "error.list", "request_id": "abc", "errors": [{"code": "token_unauthorized", "message": "Access Token Invalid"}]}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
    assert "dG9rZW4-secret" not in json.dumps(res.structured_content)


@pytest.mark.asyncio
@respx.mock
async def test_mark_read_puts_a_json_boolean():
    route = respx.put("https://api.intercom.io/conversations/471").mock(return_value=httpx.Response(200, json={"type": "conversation", "id": "471", "read": True, "state": "open"}))
    res = await _server().call_tool("mark_read", {"thread_id": "471", "message_id": "ignored"})
    assert res.is_error is False and res.structured_content["status"] == "read" and res.structured_content["raw"]["read"] is True
    assert json.loads(route.calls.last.request.content) == {"read": True}
