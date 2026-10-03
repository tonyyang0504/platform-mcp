"""Bluesky: app-password session login (createSession -> accessJwt), then XRPC calls with the JWT as bearer."""
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

SPEC = json.loads((ROOT / "catalog" / "social" / "bluesky.json").read_text(encoding="utf-8"))
DID = "did:plc:z72i7hdynmk6r22z27h6tvur"
POST = f"at://{DID}/app.bsky.feed.post/3k2yihcrp2c2a"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"identifier": "alice.bsky.social", "password": "app-pass", "did": DID}, 50, "test")
    return build_server(SPEC, transport=t)


def _login(token="JWT1"):
    # lexicons/com/atproto/server/createSession.json -> {accessJwt, refreshJwt, handle, did}
    return respx.post("https://bsky.social/xrpc/com.atproto.server.createSession").mock(
        return_value=httpx.Response(200, json={"accessJwt": token, "refreshJwt": "R", "handle": "alice.bsky.social", "did": DID}))


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "me", "publish_text", "read_comments", "read_mentions"]
    pt = next(t for t in tools if t.name == "publish_text")
    assert pt.annotations.read_only_hint is False and pt.annotations.destructive_hint is False and pt.input_schema["required"] == ["text"]
    assert next(t for t in tools if t.name == "read_comments").annotations.read_only_hint is True


@pytest.mark.asyncio
@respx.mock
async def test_publish_text_logs_in_once_then_creates_a_post_record():
    login = _login()
    # lexicons/com/atproto/repo/createRecord.json -> {uri, cid}
    route = respx.post("https://bsky.social/xrpc/com.atproto.repo.createRecord").mock(
        return_value=httpx.Response(200, json={"uri": POST, "cid": "bafyreib2rxk3rybk3aobmv5cjuql3bm2twh4jo5uxmf5lwgjq7cqqvx2lq", "validationStatus": "valid"}))
    server = _server()
    res = await server.call_tool("publish_text", {"text": "hello from platform-mcp", "reply_to": "ignored"})
    assert res.is_error is False and res.structured_content["id"] == POST
    body = json.loads(route.calls.last.request.content)
    assert body["repo"] == DID and body["collection"] == "app.bsky.feed.post"
    assert body["record"]["$type"] == "app.bsky.feed.post" and body["record"]["text"] == "hello from platform-mcp"
    assert body["record"]["createdAt"].endswith("Z") and "T" in body["record"]["createdAt"] and "reply" not in body["record"]
    assert route.calls.last.request.headers["Authorization"] == "Bearer JWT1"
    login_body = json.loads(login.calls.last.request.content)
    assert login_body == {"identifier": "alice.bsky.social", "password": "app-pass"}
    # the session is cached: a second call does not hit createSession again
    await server.call_tool("publish_text", {"text": "again"})
    assert login.call_count == 1 and route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_maps_thread_replies_and_mentions_filter_by_reason():
    _login()
    # lexicons/app/bsky/feed/getPostThread.json -> {thread: threadViewPost{post, replies[threadViewPost]}}
    respx.get("https://bsky.social/xrpc/app.bsky.feed.getPostThread").mock(return_value=httpx.Response(200, json={"thread": {
        "$type": "app.bsky.feed.defs#threadViewPost", "post": {"uri": POST, "cid": "c0", "author": {"did": DID, "handle": "alice.bsky.social"}, "record": {"text": "root"}, "indexedAt": "2026-09-24T10:00:00.000Z"},
        "replies": [{"$type": "app.bsky.feed.defs#threadViewPost", "post": {"uri": "at://did:plc:bob/app.bsky.feed.post/3k2yj", "cid": "c1", "author": {"did": "did:plc:bob", "handle": "bob.bsky.social"},
                     "record": {"$type": "app.bsky.feed.post", "text": "nice post", "createdAt": "2026-09-24T10:05:00.000Z"}, "indexedAt": "2026-09-24T10:05:01.000Z", "replyCount": 0, "likeCount": 2}}]}}))
    res = await _server().call_tool("read_comments", {"post_id": POST})
    assert res.is_error is False
    c = res.structured_content["comments"][0]
    assert c["id"] == "at://did:plc:bob/app.bsky.feed.post/3k2yj" and c["author"] == "bob.bsky.social" and c["text"] == "nice post" and c["created_at"] == "2026-09-24T10:05:01.000Z"
    assert res.structured_content["next_page"] is None
    params = respx.calls.last.request.url.params
    assert params["uri"] == POST and "limit" not in params and "page" not in params
    # lexicons/app/bsky/notification/listNotifications.json -> {cursor, notifications[{uri, cid, author, reason, record, isRead, indexedAt}]}
    respx.get("https://bsky.social/xrpc/app.bsky.notification.listNotifications").mock(return_value=httpx.Response(200, json={"notifications": [
        {"uri": "at://did:plc:bob/app.bsky.feed.post/3k2z", "cid": "c2", "author": {"did": "did:plc:bob", "handle": "bob.bsky.social"}, "reason": "mention",
         "record": {"$type": "app.bsky.feed.post", "text": "hey @alice.bsky.social", "createdAt": "2026-09-24T11:00:00.000Z"}, "isRead": False, "indexedAt": "2026-09-24T11:00:01.000Z"}]}))
    res = await _server().call_tool("read_mentions", {"limit": 10})
    m = res.structured_content["mentions"][0]
    assert m["id"] == "at://did:plc:bob/app.bsky.feed.post/3k2z" and m["author"] == "bob.bsky.social" and m["text"] == "hey @alice.bsky.social"
    params = respx.calls.last.request.url.params
    assert params["reasons"] == "mention" and params["limit"] == "10"


@pytest.mark.asyncio
@respx.mock
async def test_analytics_post_reads_counts_from_get_posts():
    _login()
    respx.get("https://bsky.social/xrpc/app.bsky.feed.getPosts").mock(return_value=httpx.Response(200, json={"posts": [
        {"uri": POST, "cid": "c0", "author": {"did": DID, "handle": "alice.bsky.social"}, "record": {"text": "root"}, "indexedAt": "2026-09-24T10:00:00.000Z",
         "replyCount": 3, "repostCount": 4, "likeCount": 5, "quoteCount": 1}]}))
    res = await _server().call_tool("analytics_post", {"post_id": POST})
    sc = res.structured_content
    assert res.is_error is False and sc["post_id"] == POST and sc["likes"] == 5 and sc["reposts"] == 4 and sc["replies"] == 3 and sc["quotes"] == 1
    assert respx.calls.last.request.url.params["uris"] == POST


@pytest.mark.asyncio
@respx.mock
async def test_bad_app_password_is_an_auth_error_result():
    respx.post("https://bsky.social/xrpc/com.atproto.server.createSession").mock(
        return_value=httpx.Response(401, json={"error": "AuthenticationRequired", "message": "Invalid identifier or password"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
    assert "app-pass" not in json.dumps(res.structured_content)
