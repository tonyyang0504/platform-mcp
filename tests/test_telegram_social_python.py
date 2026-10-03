"""Telegram as a social platform: bot token in the URL path, one configured channel chat_id, ok/result envelope."""
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

SPEC = json.loads((ROOT / "catalog" / "social" / "telegram.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"token": "123:ABC", "chat_id": "@mychannel"}, 50, "test", envelope=SPEC["adapter"]["envelope"])
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_social_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["delete", "me", "publish_image", "publish_text"]
    pt = next(t for t in tools if t.name == "publish_text")
    assert pt.annotations.read_only_hint is False and pt.input_schema["required"] == ["text"] and pt.meta["platform_mcp/endpoint"] == "/sendMessage"
    assert set(SPEC["adapter"]["not_offered"]) == {"read_comments", "reply_comment", "read_mentions", "analytics_post"}


@pytest.mark.asyncio
@respx.mock
async def test_publish_image_sends_the_first_url_as_photo_with_the_text_as_caption():
    # core.telegram.org/bots/api#sendphoto -> {ok, result: Message with photo[]}
    route = respx.post("https://api.telegram.org/bot123:ABC/sendPhoto").mock(return_value=httpx.Response(200, json={
        "ok": True, "result": {"message_id": 43, "chat": {"id": -1001, "type": "channel"}, "date": 1758700100, "caption": "pic", "photo": [{"file_id": "AgAC", "width": 90, "height": 90}]}}))
    res = await _server().call_tool("publish_image", {"text": "pic", "image_urls": ["https://img.example/a.png", "https://img.example/b.png"]})
    assert res.is_error is False and res.structured_content["id"] == "43"
    assert json.loads(route.calls.last.request.content) == {"chat_id": "@mychannel", "photo": "https://img.example/a.png", "caption": "pic"}


@pytest.mark.asyncio
@respx.mock
async def test_publish_text_sends_to_the_configured_channel_with_the_token_in_the_path():
    # core.telegram.org/bots/api#sendmessage -> {ok, result: Message}
    route = respx.post("https://api.telegram.org/bot123:ABC/sendMessage").mock(return_value=httpx.Response(200, json={
        "ok": True, "result": {"message_id": 42, "sender_chat": {"id": -1001, "title": "My channel", "type": "channel"}, "chat": {"id": -1001, "type": "channel"},
                               "date": 1758700000, "text": "hello", "reply_to_message": {"message_id": 7}}}))
    res = await _server().call_tool("publish_text", {"text": "hello", "reply_to": "7"})
    assert res.is_error is False
    assert res.structured_content["id"] == "42" and res.structured_content["raw"]["chat"]["type"] == "channel"
    req = route.calls.last.request
    assert json.loads(req.content) == {"chat_id": "@mychannel", "text": "hello", "reply_parameters": {"message_id": "7"}}
    assert "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_delete_calls_deletemessage_and_answers_a_literal_status():
    route = respx.post("https://api.telegram.org/bot123:ABC/deleteMessage").mock(return_value=httpx.Response(200, json={"ok": True, "result": True}))
    res = await _server().call_tool("delete", {"post_id": "42"})
    assert res.is_error is False and res.structured_content["status"] == "deleted"
    assert json.loads(route.calls.last.request.content) == {"chat_id": "@mychannel", "message_id": "42"}


@pytest.mark.asyncio
@respx.mock
async def test_ok_false_envelope_is_an_error_result():
    respx.post("https://api.telegram.org/bot123:ABC/deleteMessage").mock(return_value=httpx.Response(200, json={
        "ok": False, "error_code": 400, "description": "Bad Request: message can't be deleted for everyone"}))
    res = await _server().call_tool("delete", {"post_id": "1"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error" and "deleted for everyone" in res.structured_content["message"]
    respx.get("https://api.telegram.org/bot123:ABC/getMe").mock(return_value=httpx.Response(401, json={"ok": False, "error_code": 401, "description": "Unauthorized"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "123:ABC" not in json.dumps(res.structured_content)
