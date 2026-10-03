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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "discord.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"bot_token": "bot-secret-token"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_messaging_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_thread", "list_inbound", "me", "reply", "send"]
    send = next(t for t in tools if t.name == "send")
    assert send.annotations.read_only_hint is False and send.annotations.destructive_hint is False
    assert send.input_schema["required"] == ["to", "text"]
    assert send.title == "Send a message"
    assert send.meta["platform_mcp/endpoint"] == "/channels/{to}/messages"
    assert "channel id" in send.description.lower()
    li = next(t for t in tools if t.name == "list_inbound")
    assert li.annotations.read_only_hint is True
    assert set(SPEC["adapter"]["not_offered"]) == {"mark_read"}


@pytest.mark.asyncio
@respx.mock
async def test_reply_posts_a_message_reference_with_the_bot_prefixed_token():
    # docs.discord.com/developers/resources/message#create-message -> message object
    route = respx.post("https://discord.com/api/v10/channels/1001/messages").mock(return_value=httpx.Response(200, json={
        "id": "334385199974967042", "channel_id": "1001", "author": {"id": "80351110224678912", "username": "Nelly", "bot": True},
        "content": "hi", "timestamp": "2017-07-11T17:27:07.299000+00:00", "message_reference": {"message_id": "306588351130107906", "channel_id": "1001"}}))
    res = await _server().call_tool("reply", {"thread_id": "306588351130107906", "channel": "1001", "text": "hi"})
    assert res.is_error is False
    assert res.structured_content["message_id"] == "334385199974967042" and res.structured_content["status"] == "sent"
    body = json.loads(route.calls.last.request.content)
    assert body == {"content": "hi", "message_reference": {"message_id": "306588351130107906"}}
    assert route.calls.last.request.headers["Authorization"] == "Bot bot-secret-token"


@pytest.mark.asyncio
@respx.mock
async def test_send_takes_a_channel_id_and_reply_needs_the_channel():
    route = respx.post("https://discord.com/api/v10/channels/2002/messages").mock(return_value=httpx.Response(200, json={
        "id": "1", "channel_id": "2002", "author": {"id": "9", "username": "bot"}, "content": "hello", "timestamp": "2024-01-01T00:00:00+00:00"}))
    res = await _server().call_tool("send", {"to": "2002", "text": "hello", "subject": "ignored"})
    assert res.is_error is False and res.structured_content["message_id"] == "1"
    assert json.loads(route.calls.last.request.content) == {"content": "hello"}
    res = await _server().call_tool("reply", {"thread_id": "306588351130107906", "text": "hi"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and "channel" in res.structured_content["message"]


@pytest.mark.asyncio
@respx.mock
async def test_list_inbound_lists_one_channel_newest_first():
    respx.get("https://discord.com/api/v10/channels/1001/messages").mock(return_value=httpx.Response(200, json=[
        {"id": "334385199974967042", "channel_id": "1001", "author": {"id": "80351110224678912", "username": "Nelly"}, "content": "Supa dupa", "timestamp": "2017-07-11T17:27:07.299000+00:00"}]))
    res = await _server().call_tool("list_inbound", {"channel": "1001", "limit": 10})
    assert res.is_error is False
    m = res.structured_content["messages"][0]
    assert m["id"] == "334385199974967042" and m["from"] == "80351110224678912" and m["text"] == "Supa dupa"
    assert m["thread_id"] == "1001" and m["sent_at"] == "2017-07-11T17:27:07.299000+00:00"
    assert res.structured_content["next_page"] is None
    req = respx.calls.last.request
    assert req.url.params["limit"] == "10" and "since" not in req.url.params


@pytest.mark.asyncio
@respx.mock
async def test_unauthorized_is_an_auth_error_without_the_token():
    respx.get("https://discord.com/api/v10/users/@me").mock(return_value=httpx.Response(401, json={"message": "401: Unauthorized", "code": 0}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
    assert "bot-secret-token" not in json.dumps(res.structured_content)
