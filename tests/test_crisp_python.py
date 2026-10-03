import base64
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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "crisp.json").read_text(encoding="utf-8"))
BASE = "https://api.crisp.chat/v1/website/8c842203-7ed8-4e29-a608-7cf78a7d2fcc"


def _server():
    # identifier:key go into HTTP Basic; X-Crisp-Tier is a static adapter header; website_id a config field
    creds = {"identifier": "crisp-identifier", "key": "crisp-secret-key", "website_id": "8c842203-7ed8-4e29-a608-7cf78a7d2fcc"}
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_messaging_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_thread", "list_inbound", "mark_read", "me", "reply"]
    reply = next(t for t in tools if t.name == "reply")
    assert reply.annotations.read_only_hint is False and reply.annotations.destructive_hint is False
    assert reply.input_schema["required"] == ["thread_id", "text"]
    assert reply.meta["platform_mcp/endpoint"] == "/website/{website_id}/conversation/{thread_id}/message"
    mr = next(t for t in tools if t.name == "mark_read")
    assert mr.annotations.idempotent_hint is True
    assert set(SPEC["adapter"]["not_offered"]) == {"send"}


@pytest.mark.asyncio
@respx.mock
async def test_reply_sends_an_operator_text_message_with_basic_auth_and_the_tier_header():
    route = respx.post(f"{BASE}/conversation/session_19e5240f-0a8d-461e-a661-a3123fc6eec9/message").mock(return_value=httpx.Response(200, json={
        "error": False, "reason": "dispatched", "data": {"fingerprint": 163613151617340}}))
    res = await _server().call_tool("reply", {"thread_id": "session_19e5240f-0a8d-461e-a661-a3123fc6eec9", "text": "Hello there", "channel": "ignored"})
    assert res.is_error is False
    assert res.structured_content["message_id"] == "163613151617340" and res.structured_content["status"] == "dispatched"
    req = route.calls.last.request
    assert json.loads(req.content) == {"type": "text", "from": "operator", "origin": "chat", "content": "Hello there"}
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(b"crisp-identifier:crisp-secret-key").decode()
    assert req.headers["X-Crisp-Tier"] == "plugin" and SPEC["adapter"]["headers"] == {"X-Crisp-Tier": "plugin"}


@pytest.mark.asyncio
@respx.mock
async def test_list_inbound_pages_by_path_segment_and_get_thread_reads_the_last_batch():
    respx.get(f"{BASE}/conversations/2").mock(return_value=httpx.Response(200, json={
        "error": False, "reason": "listed", "data": [{"session_id": "session_19e5240f", "website_id": "8c842203", "state": "unresolved", "unread": {"operator": 1, "visitor": 0},
                                                      "last_message": "Hey there!", "updated_at": 1544451612345, "meta": {"nickname": "Valerian", "email": "valerian@crisp.chat"}}]}))
    res = await _server().call_tool("list_inbound", {"page": 2, "limit": 30, "since": "2018-03-01T17:00:00.000Z"})
    assert res.is_error is False
    m = res.structured_content["messages"][0]
    assert m["id"] == "session_19e5240f" and m["thread_id"] == "session_19e5240f" and m["from"] == "valerian@crisp.chat" and m["text"] == "Hey there!"
    req = respx.calls.last.request
    assert req.url.params["per_page"] == "30" and req.url.params["filter_date_start"] == "2018-03-01T17:00:00.000Z"

    respx.get(f"{BASE}/conversation/session_19e5240f/messages").mock(return_value=httpx.Response(200, json={
        "error": False, "reason": "listed", "data": [{"session_id": "session_19e5240f", "website_id": "8c842203", "type": "text", "from": "user", "origin": "chat",
                                                      "content": "Hey there!", "fingerprint": 163613151617340, "timestamp": 1544451612345, "user": {"nickname": "Valerian", "user_id": "session_19e5240f"}}]}))
    res = await _server().call_tool("get_thread", {"thread_id": "session_19e5240f", "limit": 5})
    assert res.is_error is False
    m = res.structured_content["messages"][0]
    assert m["id"] == "163613151617340" and m["from"] == "session_19e5240f" and m["text"] == "Hey there!" and m["raw"]["from"] == "user"
    assert "limit" not in respx.calls.last.request.url.params and "per_page" not in respx.calls.last.request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_mark_read_patches_all_visitor_messages():
    route = respx.patch(f"{BASE}/conversation/session_19e5240f/read").mock(return_value=httpx.Response(200, json={"error": False, "reason": "updated", "data": {}}))
    res = await _server().call_tool("mark_read", {"thread_id": "session_19e5240f", "message_id": "163613151617340"})
    assert res.is_error is False and res.structured_content["status"] == "updated"
    assert json.loads(route.calls.last.request.content) == {"from": "user", "origin": "chat"}


@pytest.mark.asyncio
@respx.mock
async def test_unauthorized_is_an_auth_error_without_the_credential():
    respx.get(BASE).mock(return_value=httpx.Response(401, json={"error": True, "reason": "invalid_session", "data": {}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
    assert "crisp-secret-key" not in json.dumps(res.structured_content)
