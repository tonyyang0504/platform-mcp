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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "line.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"channel_access_token": "line-secret-token"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_messaging_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["me", "send"]
    send = next(t for t in tools if t.name == "send")
    assert send.annotations.read_only_hint is False and send.annotations.destructive_hint is False
    assert send.input_schema["required"] == ["to", "text"]
    assert send.meta["platform_mcp/endpoint"] == "/v2/bot/message/push"
    me = next(t for t in tools if t.name == "me")
    assert me.annotations.read_only_hint is True
    assert set(SPEC["adapter"]["not_offered"]) == {"reply", "list_inbound", "get_thread", "mark_read"}


@pytest.mark.asyncio
@respx.mock
async def test_send_pushes_one_text_message_object_with_the_channel_access_token():
    # line-openapi PushMessageRequest {to, messages[1..5]} -> PushMessageResponse {sentMessages[{id, quoteToken}]}
    route = respx.post("https://api.line.me/v2/bot/message/push").mock(return_value=httpx.Response(200, json={
        "sentMessages": [{"id": "461230966842064897", "quoteToken": "IStG5h1Qz-..."}]}))
    res = await _server().call_tool("send", {"to": "U4af4980629...", "text": "Hello, world", "subject": "ignored", "channel": "ignored"})
    assert res.is_error is False
    assert res.structured_content["message_id"] == "461230966842064897" and res.structured_content["status"] == "sent"
    assert res.structured_content["raw"]["sentMessages"][0]["quoteToken"] == "IStG5h1Qz-..."
    body = json.loads(route.calls.last.request.content)
    assert body == {"to": "U4af4980629...", "messages": [{"type": "text", "text": "Hello, world"}]}
    assert route.calls.last.request.headers["Authorization"] == "Bearer line-secret-token"


@pytest.mark.asyncio
@respx.mock
async def test_me_reads_the_bot_info():
    respx.get("https://api.line.me/v2/bot/info").mock(return_value=httpx.Response(200, json={
        "userId": "Ub9952f8...", "basicId": "@216ru...", "displayName": "Example name", "pictureUrl": "https://obs.line-apps.com/...", "chatMode": "chat", "markAsReadMode": "manual"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["ok"] is True and res.structured_content["account"]["basicId"] == "@216ru..."


@pytest.mark.asyncio
@respx.mock
async def test_line_errors_are_error_results_without_the_token():
    respx.post("https://api.line.me/v2/bot/message/push").mock(return_value=httpx.Response(400, json={"message": "The property, 'to', in the request body is invalid (line: -, column: -)", "details": []}))
    res = await _server().call_tool("send", {"to": "bad", "text": "hi"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and "'to'" in res.structured_content["message"]
    respx.get("https://api.line.me/v2/bot/info").mock(return_value=httpx.Response(401, json={"message": "Authentication failed. Confirm that the access token in the authorization header is valid."}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
    assert "line-secret-token" not in json.dumps(res.structured_content)
