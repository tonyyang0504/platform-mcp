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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "google_chat.json").read_text(encoding="utf-8"))
C = "https://chat.googleapis.com/v1"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"client_id": "c", "client_secret": "s", "refresh_token": "r"}, 50, "test"))


def _token():
    return respx.post("https://oauth2.googleapis.com/token").mock(return_value=httpx.Response(200, json={"access_token": "ya29.C", "expires_in": 3599}))


@pytest.mark.asyncio
async def test_all_messaging_verbs_are_served():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_thread", "list_inbound", "mark_read", "me", "reply", "send"]


@pytest.mark.asyncio
@respx.mock
async def test_reply_sets_thread_name_and_reply_option():
    _token()
    route = respx.post(f"{C}/spaces/AAA/messages").mock(return_value=httpx.Response(200, json={"name": "spaces/AAA/messages/m.2", "thread": {"name": "spaces/AAA/threads/t1"}}))
    res = await _server().call_tool("reply", {"thread_id": "spaces/AAA/threads/t1", "channel": "AAA", "text": "ok"})
    assert res.is_error is False and res.structured_content["message_id"] == "spaces/AAA/messages/m.2"
    assert route.calls.last.request.url.params["messageReplyOption"] == "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD"
    assert json.loads(route.calls.last.request.content) == {"text": "ok", "thread": {"name": "spaces/AAA/threads/t1"}}
    assert route.calls.last.request.headers["Authorization"] == "Bearer ya29.C"


@pytest.mark.asyncio
@respx.mock
async def test_get_thread_filters_by_thread_name():
    _token()
    respx.get(f"{C}/spaces/AAA/messages").mock(return_value=httpx.Response(200, json={"messages": [
        {"name": "spaces/AAA/messages/m1", "sender": {"name": "users/1"}, "text": "hi", "createTime": "2026-09-24T10:00:00Z", "thread": {"name": "spaces/AAA/threads/t1"}}]}))
    res = await _server().call_tool("get_thread", {"thread_id": "spaces/AAA/threads/t1", "channel": "AAA"})
    m = res.structured_content["messages"][0]
    assert m["from"] == "users/1" and m["thread_id"] == "spaces/AAA/threads/t1"
    assert respx.calls.last.request.url.params["filter"] == "thread.name = spaces/AAA/threads/t1"


@pytest.mark.asyncio
@respx.mock
async def test_mark_read_patches_space_read_state():
    _token()
    route = respx.patch(f"{C}/users/me/spaces/AAA/spaceReadState").mock(return_value=httpx.Response(200, json={"name": "users/me/spaces/AAA/spaceReadState"}))
    res = await _server().call_tool("mark_read", {"channel": "AAA"})
    assert res.structured_content["status"] == "read"
    assert route.calls.last.request.url.params["updateMask"] == "lastReadTime"
    assert json.loads(route.calls.last.request.content)["lastReadTime"].endswith("Z")
