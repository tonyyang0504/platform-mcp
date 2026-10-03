"""Discord as a social platform: bot token, one configured channel, forum-thread ids as post ids."""
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

SPEC = json.loads((ROOT / "catalog" / "social" / "discord.json").read_text(encoding="utf-8"))


def _server():
    # channel_id is a non-secret config field: publish_text / reply_comment / delete address /channels/<channel_id>/...
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"bot_token": "bot-secret-token", "channel_id": "1001"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_social_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["delete", "me", "publish_image", "publish_text", "read_comments", "reply_comment"]
    pt = next(t for t in tools if t.name == "publish_text")
    assert pt.annotations.read_only_hint is False and pt.annotations.destructive_hint is False and pt.input_schema["required"] == ["text"]
    assert pt.meta["platform_mcp/endpoint"] == "/channels/{channel_id}/messages"
    d = next(t for t in tools if t.name == "delete")
    assert d.annotations.destructive_hint is True
    assert set(SPEC["adapter"]["not_offered"]) == {"read_mentions", "analytics_post"}


@pytest.mark.asyncio
@respx.mock
async def test_publish_image_sends_one_embed_per_image_url():
    # docs.discord.com/developers/resources/message#create-message -> embeds[].image.url (Embed Image Structure)
    route = respx.post("https://discord.com/api/v10/channels/1001/messages").mock(return_value=httpx.Response(200, json={
        "id": "5", "channel_id": "1001", "author": {"id": "9", "username": "bot"}, "content": "pics", "timestamp": "2026-09-24T12:00:00+00:00",
        "embeds": [{"type": "image", "image": {"url": "https://img.example/a.png"}}, {"type": "image", "image": {"url": "https://img.example/b.png"}}]}))
    res = await _server().call_tool("publish_image", {"text": "pics", "image_urls": ["https://img.example/a.png", "https://img.example/b.png"]})
    assert res.is_error is False and res.structured_content["id"] == "5"
    assert json.loads(route.calls.last.request.content) == {"content": "pics", "embeds": [{"image": {"url": "https://img.example/a.png"}}, {"image": {"url": "https://img.example/b.png"}}]}
    # text is optional: an image-only message carries embeds alone
    await _server().call_tool("publish_image", {"image_urls": ["https://img.example/a.png"]})
    assert json.loads(route.calls.last.request.content) == {"embeds": [{"image": {"url": "https://img.example/a.png"}}]}


@pytest.mark.asyncio
@respx.mock
async def test_publish_text_posts_into_the_configured_channel_with_a_reply_reference():
    # docs.discord.com/developers/resources/message#create-message -> message object
    route = respx.post("https://discord.com/api/v10/channels/1001/messages").mock(return_value=httpx.Response(200, json={
        "id": "334385199974967042", "channel_id": "1001", "author": {"id": "80351110224678912", "username": "Nelly", "bot": True},
        "content": "hello", "timestamp": "2017-07-11T17:27:07.299000+00:00", "message_reference": {"message_id": "306588351130107906", "channel_id": "1001"}}))
    res = await _server().call_tool("publish_text", {"text": "hello", "reply_to": "306588351130107906"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "334385199974967042" and sc["created_at"] == "2017-07-11T17:27:07.299000+00:00" and sc["raw"]["channel_id"] == "1001"
    req = route.calls.last.request
    assert json.loads(req.content) == {"content": "hello", "message_reference": {"message_id": "306588351130107906"}}
    assert req.headers["Authorization"] == "Bot bot-secret-token"


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_lists_the_thread_named_by_post_id():
    # a forum post's thread id equals its starter message id, so post_id is the thread (channel) id
    respx.get("https://discord.com/api/v10/channels/5555/messages").mock(return_value=httpx.Response(200, json=[
        {"id": "2", "channel_id": "5555", "author": {"id": "9", "username": "zsc"}, "content": "second", "timestamp": "2026-09-24T10:05:00+00:00"},
        {"id": "1", "channel_id": "5555", "author": {"id": "8", "username": "op"}, "content": "first", "timestamp": "2026-09-24T10:00:00+00:00"}]))
    res = await _server().call_tool("read_comments", {"post_id": "5555", "limit": 10, "page": 3})
    assert res.is_error is False
    c = res.structured_content["comments"][0]
    assert c["id"] == "2" and c["author"] == "zsc" and c["text"] == "second" and c["created_at"] == "2026-09-24T10:05:00+00:00"
    assert res.structured_content["next_page"] is None
    params = respx.calls.last.request.url.params
    assert params["limit"] == "10" and "page" not in params


@pytest.mark.asyncio
@respx.mock
async def test_delete_answers_a_literal_status_for_the_204():
    route = respx.delete("https://discord.com/api/v10/channels/1001/messages/42").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("delete", {"post_id": "42"})
    assert res.is_error is False and res.structured_content["status"] == "deleted"
    assert route.call_count == 1 and route.calls.last.request.headers["Authorization"] == "Bot bot-secret-token"


@pytest.mark.asyncio
@respx.mock
async def test_unauthorized_is_an_auth_error_without_the_token():
    respx.get("https://discord.com/api/v10/users/@me").mock(return_value=httpx.Response(401, json={"message": "401: Unauthorized", "code": 0}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
    assert "bot-secret-token" not in json.dumps(res.structured_content)
