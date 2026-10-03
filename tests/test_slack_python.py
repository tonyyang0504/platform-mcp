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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "slack.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"token": "xoxb-test"}, 50, "test", envelope=SPEC["adapter"]["envelope"])
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_messaging_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_thread", "list_inbound", "mark_read", "me", "reply", "send"]
    send = next(t for t in tools if t.name == "send")
    assert send.annotations.read_only_hint is False and send.annotations.destructive_hint is False
    assert send.input_schema["required"] == ["to", "text"]
    assert send.title == "Send a message"
    assert send.meta["platform_mcp/endpoint"] == "/chat.postMessage"
    reply = next(t for t in tools if t.name == "reply")
    assert "channel" in reply.input_schema["properties"]


@pytest.mark.asyncio
@respx.mock
async def test_reply_posts_thread_ts_and_channel_with_a_bearer_token():
    route = respx.post("https://slack.com/api/chat.postMessage").mock(return_value=httpx.Response(200, json={
        "ok": True, "channel": "C123", "ts": "1503435956.000247", "message": {"type": "message", "text": "hi", "ts": "1503435956.000247"}}))
    res = await _server().call_tool("reply", {"thread_id": "1503435900.000100", "channel": "C123", "text": "hi"})
    assert res.is_error is False
    assert res.structured_content["message_id"] == "1503435956.000247"
    body = json.loads(route.calls.last.request.content)
    assert body == {"channel": "C123", "thread_ts": "1503435900.000100", "text": "hi"}
    assert route.calls.last.request.headers["Authorization"] == "Bearer xoxb-test"


@pytest.mark.asyncio
@respx.mock
async def test_list_inbound_lists_one_channel():
    respx.get("https://slack.com/api/conversations.history").mock(return_value=httpx.Response(200, json={
        "ok": True, "messages": [{"type": "message", "user": "U012AB3CDE", "text": "I find you punny", "ts": "1512085950.000216", "thread_ts": "1512085950.000216"}],
        "has_more": False, "response_metadata": {"next_cursor": ""}}))
    res = await _server().call_tool("list_inbound", {"channel": "C123", "limit": 10})
    assert res.is_error is False
    m = res.structured_content["messages"][0]
    assert m["id"] == "1512085950.000216" and m["from"] == "U012AB3CDE" and m["text"] == "I find you punny"
    assert res.structured_content["next_page"] is None
    req = respx.calls.last.request
    assert req.url.params["channel"] == "C123" and req.url.params["limit"] == "10"


@pytest.mark.asyncio
@respx.mock
async def test_ok_false_envelope_is_an_is_error_result():
    respx.get("https://slack.com/api/conversations.replies").mock(return_value=httpx.Response(200, json={"ok": False, "error": "channel_not_found"}))
    res = await _server().call_tool("get_thread", {"thread_id": "1503435900.000100", "channel": "C404"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
    assert "channel_not_found" in res.structured_content["message"]
    respx.post("https://slack.com/api/auth.test").mock(return_value=httpx.Response(200, json={"ok": False, "error": "invalid_auth"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
