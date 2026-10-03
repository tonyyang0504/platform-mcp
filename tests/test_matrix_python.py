import json
import sys
from pathlib import Path
from urllib.parse import unquote

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "messaging" / "matrix.json").read_text(encoding="utf-8"))


def _server():
    # `homeserver` is a non-secret config field: every tool path is https://{homeserver}/_matrix/client/...
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"access_token": "syt_secret_token", "homeserver": "matrix.example.org"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_messaging_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_thread", "list_inbound", "mark_read", "me", "reply", "send"]
    send = next(t for t in tools if t.name == "send")
    assert send.annotations.read_only_hint is False and send.input_schema["required"] == ["to", "text"]
    li = next(t for t in tools if t.name == "list_inbound")
    assert li.annotations.read_only_hint is True and li.annotations.idempotent_hint is True
    assert li.input_schema["required"] == [] and li.output_schema["required"] == ["messages"]
    assert li.meta["platform_mcp/endpoint"] == "https://{homeserver}/_matrix/client/v3/rooms/{channel}/messages"
    assert SPEC["adapter"]["not_offered"] == {}


@pytest.mark.asyncio
@respx.mock
async def test_me_calls_whoami_on_the_configured_homeserver_with_a_bearer_token():
    route = respx.get("https://matrix.example.org/_matrix/client/v3/account/whoami").mock(return_value=httpx.Response(200, json={"device_id": "ABC1234", "user_id": "@joe:example.org"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["ok"] is True and res.structured_content["account"]["user_id"] == "@joe:example.org"
    assert route.calls.last.request.headers["Authorization"] == "Bearer syt_secret_token"


@pytest.mark.asyncio
@respx.mock
async def test_list_inbound_reads_one_room_backwards_from_the_live_edge():
    respx.get(url__regex=r"https://matrix\.example\.org/_matrix/client/v3/rooms/.*/messages.*").mock(return_value=httpx.Response(200, json={
        "start": "t47409-4357353_219380_26003_2265", "end": "t47409-4357353_219380_26003_2265",
        "chunk": [{"event_id": "$143273582443PhrSn:example.org", "room_id": "!636q39766251:example.com", "sender": "@example:example.org", "type": "m.room.message",
                   "origin_server_ts": 1432735824653, "content": {"body": "This is an example text message", "msgtype": "m.text"}},
                  {"event_id": "$state1:example.org", "room_id": "!636q39766251:example.com", "sender": "@example:example.org", "type": "m.room.name",
                   "origin_server_ts": 1432735824000, "content": {"name": "The room name"}}]}))
    res = await _server().call_tool("list_inbound", {"channel": "!636q39766251:example.com", "limit": 10})
    assert res.is_error is False
    m = res.structured_content["messages"]
    assert m[0]["id"] == "$143273582443PhrSn:example.org" and m[0]["from"] == "@example:example.org" and m[0]["text"] == "This is an example text message"
    assert m[0]["thread_id"] == "!636q39766251:example.com" and m[1]["text"] is None and m[1]["raw"]["type"] == "m.room.name"
    req = respx.calls.last.request
    assert unquote(req.url.path) == "/_matrix/client/v3/rooms/!636q39766251:example.com/messages"
    assert req.url.params["dir"] == "b" and req.url.params["limit"] == "10" and "from" not in req.url.params


@pytest.mark.asyncio
@respx.mock
async def test_get_thread_reads_m_thread_relations_of_the_root_event():
    respx.get(url__regex=r"https://matrix\.example\.org/_matrix/client/v1/rooms/.*/relations/.*/m\.thread.*").mock(return_value=httpx.Response(200, json={
        "chunk": [{"event_id": "$reply1:example.org", "room_id": "!636q39766251:example.com", "sender": "@bob:example.org", "type": "m.room.message",
                   "origin_server_ts": 1432735825000, "content": {"body": "reply in thread", "msgtype": "m.text", "m.relates_to": {"rel_type": "m.thread", "event_id": "$root:example.org"}}}]}))
    res = await _server().call_tool("get_thread", {"thread_id": "$root:example.org", "channel": "!636q39766251:example.com"})
    assert res.is_error is False
    assert res.structured_content["messages"][0]["id"] == "$reply1:example.org" and res.structured_content["messages"][0]["text"] == "reply in thread"
    assert unquote(respx.calls.last.request.url.path) == "/_matrix/client/v1/rooms/!636q39766251:example.com/relations/$root:example.org/m.thread"
    res = await _server().call_tool("get_thread", {"thread_id": "$root:example.org"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and "channel" in res.structured_content["message"]


@pytest.mark.asyncio
@respx.mock
async def test_unknown_token_is_an_auth_error_without_the_token():
    respx.get("https://matrix.example.org/_matrix/client/v3/account/whoami").mock(return_value=httpx.Response(401, json={"errcode": "M_UNKNOWN_TOKEN", "error": "Unrecognised access token."}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
    assert "syt_secret_token" not in json.dumps(res.structured_content)


@pytest.mark.asyncio
@respx.mock
async def test_send_puts_an_m_text_event_with_a_fresh_uuid_txn_id():
    route = respx.put(url__regex=r"https://matrix\.example\.org/_matrix/client/v3/rooms/.*/send/m\.room\.message/[0-9a-f-]{36}$").mock(return_value=httpx.Response(200, json={"event_id": "$YUwRidLecu:example.com"}))
    res = await _server().call_tool("send", {"to": "!636q39766251:example.com", "text": "hello"})
    assert res.is_error is False and res.structured_content["message_id"] == "$YUwRidLecu:example.com" and res.structured_content["status"] == "sent"
    assert json.loads(route.calls.last.request.content) == {"msgtype": "m.text", "body": "hello"}
    assert unquote(route.calls.last.request.url.path).startswith("/_matrix/client/v3/rooms/!636q39766251:example.com/send/m.room.message/")
    await _server().call_tool("send", {"to": "!636q39766251:example.com", "text": "again"})
    assert route.calls[0].request.url.path != route.calls[1].request.url.path


@pytest.mark.asyncio
@respx.mock
async def test_mark_read_posts_an_m_read_receipt_and_accepts_the_empty_answer():
    route = respx.post(url__regex=r"https://matrix\.example\.org/_matrix/client/v3/rooms/.*/receipt/m\.read/.*").mock(return_value=httpx.Response(200, json={}))
    res = await _server().call_tool("mark_read", {"channel": "!636q39766251:example.com", "message_id": "$YUwRidLecu:example.com"})
    assert res.is_error is False and res.structured_content["status"] == "read"
    assert unquote(route.calls.last.request.url.path) == "/_matrix/client/v3/rooms/!636q39766251:example.com/receipt/m.read/$YUwRidLecu:example.com"
    assert route.calls.last.request.content == b""
    res = await _server().call_tool("mark_read", {"message_id": "$YUwRidLecu:example.com"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_reply_sends_a_threaded_event_with_m_relates_to():
    route = respx.put(url__regex=r"https://matrix\.example\.org/_matrix/client/v3/rooms/.*/send/m\.room\.message/[0-9a-f-]{36}$").mock(return_value=httpx.Response(200, json={"event_id": "$reply2:example.com"}))
    res = await _server().call_tool("reply", {"thread_id": "$root:example.org", "channel": "!636q39766251:example.com", "text": "in thread"})
    assert res.is_error is False and res.structured_content["message_id"] == "$reply2:example.com"
    assert json.loads(route.calls.last.request.content) == {
        "msgtype": "m.text", "body": "in thread",
        "m.relates_to": {"rel_type": "m.thread", "event_id": "$root:example.org", "is_falling_back": True, "m.in_reply_to": {"event_id": "$root:example.org"}}}
    assert unquote(route.calls.last.request.url.path).startswith("/_matrix/client/v3/rooms/!636q39766251:example.com/send/m.room.message/")
    res = await _server().call_tool("reply", {"thread_id": "$root:example.org", "text": "no room"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"
