"""Lemmy: session login on the configured instance (user/login -> jwt), integer ids on writes, /api/v3 paths."""
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

SPEC = json.loads((ROOT / "catalog" / "social" / "lemmy.json").read_text(encoding="utf-8"))
CREDS = {"username_or_email": "alice", "password": "pw-secret", "instance": "lemmy.example", "community_id": "42"}


def _server(creds=CREDS):
    # `instance` and `community_id` are config fields: the login URL and every tool path are https://{instance}/api/v3/...
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds, 50, "test")
    return build_server(SPEC, transport=t)


def _login(token="JWT1"):
    # lemmy-js-client 0.19.4 LoginResponse {jwt?, registration_created, verify_email_sent}
    return respx.post("https://lemmy.example/api/v3/user/login").mock(return_value=httpx.Response(200, json={"jwt": token, "registration_created": False, "verify_email_sent": False}))


def _post_response(post_id=123):
    return {"post_view": {"post": {"id": post_id, "name": "hello", "body": "hello", "creator_id": 1, "community_id": 42, "removed": False, "locked": False,
                                   "published": "2026-09-24T09:00:00.000Z", "deleted": False, "nsfw": False, "ap_id": f"https://lemmy.example/post/{post_id}", "local": True, "language_id": 0},
                          "creator": {"id": 1, "name": "alice"}, "community": {"id": 42, "name": "test"}, "counts": {"post_id": post_id, "comments": 0, "score": 1, "upvotes": 1, "downvotes": 0}}}


@pytest.mark.asyncio
async def test_tools_follow_the_social_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "delete", "me", "publish_image", "publish_text", "read_comments", "read_mentions"]
    pt = next(t for t in tools if t.name == "publish_text")
    assert pt.annotations.read_only_hint is False and pt.input_schema["required"] == ["text"]
    assert next(t for t in tools if t.name == "delete").annotations.destructive_hint is True
    assert set(SPEC["adapter"]["not_offered"]) == {"reply_comment"}


@pytest.mark.asyncio
@respx.mock
async def test_publish_text_logs_in_on_the_instance_then_posts_with_an_integer_community_id():
    login = _login()
    route = respx.post("https://lemmy.example/api/v3/post").mock(return_value=httpx.Response(200, json=_post_response()))
    server = _server()
    res = await server.call_tool("publish_text", {"text": "hello", "reply_to": "ignored"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "123" and sc["url"] == "https://lemmy.example/post/123" and sc["created_at"].startswith("2026-09-24")
    assert json.loads(login.calls.last.request.content) == {"username_or_email": "alice", "password": "pw-secret"}
    body = json.loads(route.calls.last.request.content)
    assert body == {"name": "hello", "body": "hello", "community_id": 42} and isinstance(body["community_id"], int)
    assert route.calls.last.request.headers["Authorization"] == "Bearer JWT1"
    # the session is cached: a second write does not log in again
    await server.call_tool("publish_image", {"text": "a picture", "image_urls": ["https://img.example/a.png", "https://img.example/b.png"]})
    assert login.call_count == 1 and route.call_count == 2
    assert json.loads(route.calls.last.request.content) == {"name": "a picture", "url": "https://img.example/a.png", "community_id": 42}


@pytest.mark.asyncio
@respx.mock
async def test_delete_sends_an_integer_post_id_and_rejects_a_non_numeric_one():
    _login()
    route = respx.post("https://lemmy.example/api/v3/post/delete").mock(return_value=httpx.Response(200, json=_post_response()))
    res = await _server().call_tool("delete", {"post_id": "123"})
    assert res.is_error is False and res.structured_content["status"] == "deleted" and res.structured_content["raw"]["post_view"]["post"]["id"] == 123
    assert json.loads(route.calls.last.request.content) == {"post_id": 123, "deleted": True}
    res = await _server().call_tool("delete", {"post_id": "https://lemmy.example/post/123"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_pages_the_comment_list_and_caps_limit_at_50():
    _login()
    # lemmy-js-client 0.19.4 GetCommentsResponse {comments: CommentView[]}
    route = respx.get("https://lemmy.example/api/v3/comment/list").mock(return_value=httpx.Response(200, json={"comments": [
        {"comment": {"id": 987, "creator_id": 5, "post_id": 123, "content": "nice post", "removed": False, "published": "2026-09-24T10:05:00.123456Z", "deleted": False,
                     "ap_id": "https://lemmy.example/comment/987", "local": True, "path": "0.987", "distinguished": False, "language_id": 0},
         "creator": {"id": 5, "name": "zsc", "banned": False, "actor_id": "https://lemmy.example/u/zsc", "local": True, "deleted": False, "bot_account": False, "instance_id": 1},
         "post": {"id": 123, "name": "A post"}, "community": {"id": 42, "name": "test"}, "counts": {"comment_id": 987, "score": 3, "upvotes": 3, "downvotes": 0, "child_count": 0}}]}))
    res = await _server().call_tool("read_comments", {"post_id": "123", "page": 2, "limit": 60})
    assert res.is_error is False
    c = res.structured_content["comments"][0]
    assert c["id"] == "987" and c["author"] == "zsc" and c["text"] == "nice post" and c["created_at"].startswith("2026-09-24T10:05")
    assert res.structured_content["next_page"] is None
    req = route.calls.last.request
    assert req.url.params["post_id"] == "123" and req.url.params["page"] == "2" and req.url.params["limit"] == "50"
    assert req.headers["Authorization"] == "Bearer JWT1"
    # analytics: GET /post?id= -> post_view.counts
    respx.get("https://lemmy.example/api/v3/post").mock(return_value=httpx.Response(200, json={**_post_response(), "community_view": {}, "moderators": [], "cross_posts": []}))
    res = await _server().call_tool("analytics_post", {"post_id": "123"})
    assert res.is_error is False and res.structured_content["post_id"] == "123" and res.structured_content["upvotes"] == 1
    assert respx.calls.last.request.url.params["id"] == "123"


@pytest.mark.asyncio
@respx.mock
async def test_bad_password_is_an_auth_error_without_the_secret():
    respx.post("https://lemmy.example/api/v3/user/login").mock(return_value=httpx.Response(400, json={"error": "incorrect_login"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 400
    assert "pw-secret" not in json.dumps(res.structured_content)
