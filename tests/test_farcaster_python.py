"""Farcaster via Neynar: x-api-key header, signer_uuid + fid config fields, cast hashes as post ids."""
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

SPEC = json.loads((ROOT / "catalog" / "social" / "farcaster.json").read_text(encoding="utf-8"))
SIGNER = "19d0c5fd-9b33-4a48-a0e2-bc7b0555baec"
HASH = "0x71d5225f77e0164388b1d4c120825f3a2c1f131c"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "neynar-key", "signer_uuid": SIGNER, "fid": "3"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_social_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "delete", "me", "publish_image", "publish_text", "read_comments", "read_mentions", "reply_comment"]
    pt = next(t for t in tools if t.name == "publish_text")
    assert pt.annotations.read_only_hint is False and pt.input_schema["required"] == ["text"] and pt.meta["platform_mcp/endpoint"] == "/v2/farcaster/cast/"
    assert SPEC["adapter"]["not_offered"] == {}


@pytest.mark.asyncio
@respx.mock
async def test_publish_image_sends_up_to_two_url_embeds():
    # docs.neynar.com/reference/publish-cast -> embeds: array (maxItems 2) of {url} | {cast_id}
    route = respx.post("https://api.neynar.com/v2/farcaster/cast/").mock(return_value=httpx.Response(200, json={"success": True, "cast": {"hash": HASH, "author": {"fid": 3}, "text": "pics"}}))
    res = await _server().call_tool("publish_image", {"text": "pics", "image_urls": ["https://img.example/a.png", "https://img.example/b.png", "https://img.example/c.png"]})
    assert res.is_error is False and res.structured_content["id"] == HASH
    assert json.loads(route.calls.last.request.content) == {"signer_uuid": SIGNER, "text": "pics", "embeds": [{"url": "https://img.example/a.png"}, {"url": "https://img.example/b.png"}]}
    await _server().call_tool("publish_image", {"image_urls": ["https://img.example/a.png"]})
    assert json.loads(route.calls.last.request.content) == {"signer_uuid": SIGNER, "embeds": [{"url": "https://img.example/a.png"}]}


@pytest.mark.asyncio
@respx.mock
async def test_publish_text_and_reply_comment_post_a_cast_with_the_signer():
    # docs.neynar.com/reference/publish-cast -> {success, cast{hash, author{fid}, text}}
    route = respx.post("https://api.neynar.com/v2/farcaster/cast/").mock(return_value=httpx.Response(200, json={
        "success": True, "cast": {"hash": HASH, "author": {"fid": 3}, "text": "gm"}}))
    server = _server()
    res = await server.call_tool("publish_text", {"text": "gm"})
    assert res.is_error is False and res.structured_content["id"] == HASH
    req = route.calls.last.request
    assert json.loads(req.content) == {"signer_uuid": SIGNER, "text": "gm"} and req.headers["x-api-key"] == "neynar-key" and "Authorization" not in req.headers
    res = await server.call_tool("reply_comment", {"comment_id": "0xabc", "text": "thanks"})
    assert res.is_error is False and res.structured_content["id"] == HASH
    assert json.loads(route.calls.last.request.content) == {"signer_uuid": SIGNER, "text": "thanks", "parent": "0xabc"}


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_and_mentions_use_hash_lookups_and_the_configured_fid():
    # docs.neynar.com/reference/lookup-cast-conversation -> {conversation{cast{direct_replies[]}}, next{cursor}}
    respx.get("https://api.neynar.com/v2/farcaster/cast/conversation/").mock(return_value=httpx.Response(200, json={"conversation": {"cast": {
        "hash": HASH, "text": "root", "direct_replies": [
            {"hash": "0xreply1", "author": {"fid": 5, "username": "zsc"}, "text": "nice", "timestamp": "2026-09-24T10:05:00.000Z", "direct_replies": []}]}}, "next": {"cursor": None}}))
    res = await _server().call_tool("read_comments", {"post_id": HASH, "limit": 30, "page": 2})
    assert res.is_error is False
    c = res.structured_content["comments"][0]
    assert c["id"] == "0xreply1" and c["author"] == "zsc" and c["text"] == "nice" and c["created_at"] == "2026-09-24T10:05:00.000Z"
    params = respx.calls.last.request.url.params
    assert params["identifier"] == HASH and params["type"] == "hash" and params["reply_depth"] == "1" and params["limit"] == "30" and "page" not in params
    # docs.neynar.com/reference/fetch-all-notifications -> {unseen_notifications_count, notifications[{type, cast{...}}], next{cursor}}
    respx.get("https://api.neynar.com/v2/farcaster/notifications/").mock(return_value=httpx.Response(200, json={"unseen_notifications_count": 1, "notifications": [
        {"type": "mention", "most_recent_timestamp": "2026-09-24T11:00:00.000Z", "seen": False,
         "cast": {"hash": "0xmention", "author": {"fid": 5, "username": "zsc"}, "text": "hey @me", "timestamp": "2026-09-24T11:00:00.000Z"}}], "next": {"cursor": None}}))
    res = await _server().call_tool("read_mentions", {"since": "ignored"})
    m = res.structured_content["mentions"][0]
    assert m["id"] == "0xmention" and m["author"] == "zsc" and m["text"] == "hey @me"
    params = respx.calls.last.request.url.params
    assert params["fid"] == "3" and params["type"] == "mentions" and params["limit"] == "15" and "since" not in params


@pytest.mark.asyncio
@respx.mock
async def test_delete_sends_a_json_body_with_the_target_hash_and_analytics_maps_reaction_counts():
    route = respx.delete("https://api.neynar.com/v2/farcaster/cast/").mock(return_value=httpx.Response(200, json={"success": True, "message": "Cast deleted"}))
    res = await _server().call_tool("delete", {"post_id": HASH})
    assert res.is_error is False and res.structured_content["status"] == "deleted" and res.structured_content["raw"]["success"] is True
    assert json.loads(route.calls.last.request.content) == {"signer_uuid": SIGNER, "target_hash": HASH}
    # docs.neynar.com/reference/lookup-cast-by-hash-or-url -> {cast{hash, reactions{likes_count, recasts_count}, replies{count}}}
    respx.get("https://api.neynar.com/v2/farcaster/cast/").mock(return_value=httpx.Response(200, json={"cast": {
        "hash": HASH, "author": {"fid": 3, "username": "me"}, "text": "gm", "timestamp": "2026-09-24T09:00:00.000Z",
        "reactions": {"likes_count": 12, "recasts_count": 4, "likes": [], "recasts": []}, "replies": {"count": 2}}}))
    res = await _server().call_tool("analytics_post", {"post_id": HASH})
    sc = res.structured_content
    assert res.is_error is False and sc["post_id"] == HASH and sc["likes"] == 12 and sc["recasts"] == 4 and sc["replies"] == 2
    params = respx.calls.last.request.url.params
    assert params["identifier"] == HASH and params["type"] == "hash"


@pytest.mark.asyncio
@respx.mock
async def test_me_looks_up_the_configured_fid_and_a_bad_key_is_an_auth_error():
    respx.get("https://api.neynar.com/v2/farcaster/user/bulk/").mock(return_value=httpx.Response(200, json={"users": [{"fid": 3, "username": "me", "display_name": "Me", "follower_count": 10}]}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["ok"] is True and res.structured_content["account"]["users"][0]["username"] == "me"
    assert respx.calls.last.request.url.params["fids"] == "3"
    respx.get("https://api.neynar.com/v2/farcaster/user/bulk/").mock(return_value=httpx.Response(401, json={"code": "Unauthorized", "message": "Invalid API key"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and "neynar-key" not in json.dumps(res.structured_content)
