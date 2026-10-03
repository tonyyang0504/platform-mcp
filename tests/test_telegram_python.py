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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "telegram.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"token": "123:ABC"}, 50, "test", envelope=SPEC["adapter"]["envelope"])
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_messaging_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["list_inbound", "me", "send"]  # reply / get_thread / mark_read are not offered
    send = next(t for t in tools if t.name == "send")
    assert send.annotations.read_only_hint is False and send.annotations.destructive_hint is False
    assert send.input_schema["required"] == ["to", "text"]
    assert send.meta["platform_mcp/endpoint"] == "/sendMessage"
    assert set(SPEC["adapter"]["not_offered"]) == {"reply", "get_thread", "mark_read"}


@pytest.mark.asyncio
@respx.mock
async def test_send_puts_the_token_in_the_path_and_maps_the_result():
    route = respx.post("https://api.telegram.org/bot123:ABC/sendMessage").mock(return_value=httpx.Response(200, json={
        "ok": True, "result": {"message_id": 42, "date": 1700000000, "chat": {"id": 987, "type": "private"}, "from": {"id": 1, "is_bot": True}, "text": "hello"}}))
    res = await _server().call_tool("send", {"to": "987", "text": "hello"})
    assert res.is_error is False
    assert res.structured_content["message_id"] == "42" and res.structured_content["raw"]["chat"]["id"] == 987
    assert json.loads(route.calls.last.request.content) == {"chat_id": "987", "text": "hello"}
    assert "Authorization" not in route.calls.last.request.headers


@pytest.mark.asyncio
@respx.mock
async def test_list_inbound_polls_get_updates_without_an_offset():
    respx.get("https://api.telegram.org/bot123:ABC/getUpdates").mock(return_value=httpx.Response(200, json={
        "ok": True, "result": [{"update_id": 1001, "message": {"message_id": 5, "date": 1700000000, "chat": {"id": 987, "type": "private"}, "text": "hi bot"}}]}))
    res = await _server().call_tool("list_inbound", {"limit": 10})
    assert res.is_error is False
    m = res.structured_content["messages"][0]
    assert m["id"] == "1001" and m["text"] == "hi bot"
    req = respx.calls.last.request
    assert req.url.params["limit"] == "10" and "offset" not in req.url.params


@pytest.mark.asyncio
@respx.mock
async def test_ok_false_envelope_is_an_is_error_result():
    respx.get("https://api.telegram.org/bot123:ABC/getMe").mock(return_value=httpx.Response(200, json={"ok": False, "error_code": 401, "description": "Unauthorized"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    respx.post("https://api.telegram.org/bot123:ABC/sendMessage").mock(return_value=httpx.Response(200, json={"ok": False, "error_code": 400, "description": "Bad Request: chat not found"}))
    res = await _server().call_tool("send", {"to": "0", "text": "x"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error" and "chat not found" in res.structured_content["message"]
