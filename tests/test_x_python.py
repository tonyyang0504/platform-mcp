"""X API v2: OAuth 2.0 refresh grant (confidential client, HTTP Basic), posts, mentions, metrics."""
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

import base64  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "social" / "x.json").read_text(encoding="utf-8"))
TOKEN_URL = "https://api.x.com/2/oauth2/token"
CREDS = {"client_id": "CLIENTID", "client_secret": "CLIENTSECRET", "refresh_token": "REFRESHsecret", "user_id": "2244994945"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], dict(CREDS), 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"token_type": "bearer", "expires_in": 7200, "access_token": "ACCESS1", "scope": "tweet.read tweet.write users.read offline.access", "refresh_token": "REFRESH2"}))


@pytest.mark.asyncio
@respx.mock
async def test_refresh_grant_uses_basic_auth_and_publish_sends_reply_object():
    token = _token()
    route = respx.post("https://api.x.com/2/tweets").mock(return_value=httpx.Response(201, json={"data": {"id": "1445880548472328192", "text": "hi"}}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["analytics_post", "delete", "me", "publish_text", "read_comments", "read_mentions", "reply_comment"]
    res = await server.call_tool("publish_text", {"text": "hi", "reply_to": "1445880548472328100"})
    assert res.is_error is False and res.structured_content["id"] == "1445880548472328192"
    treq = token.calls.last.request
    assert parse_qs(treq.content.decode()) == {"grant_type": ["refresh_token"], "refresh_token": ["REFRESHsecret"]}
    assert treq.headers["Authorization"] == "Basic " + base64.b64encode(b"CLIENTID:CLIENTSECRET").decode()
    req = route.calls.last.request
    assert json.loads(req.content) == {"text": "hi", "reply": {"in_reply_to_tweet_id": "1445880548472328100"}} and req.headers["Authorization"] == "Bearer ACCESS1"


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_searches_the_conversation():
    _token()
    respx.get("https://api.x.com/2/tweets/search/recent").mock(return_value=httpx.Response(200, json={
        "data": [{"id": "2", "text": "@me reply", "author_id": "77", "created_at": "2026-09-24T10:00:00.000Z", "conversation_id": "1"}], "meta": {"result_count": 1}}))
    res = await _server().call_tool("read_comments", {"post_id": "1", "limit": 10})
    c = res.structured_content["comments"][0]
    assert c["id"] == "2" and c["author"] == "77" and c["created_at"].startswith("2026-09-24")
    params = respx.calls.last.request.url.params
    assert params["query"] == "conversation_id:1" and params["max_results"] == "10" and params["post.fields"].startswith("author_id")


@pytest.mark.asyncio
@respx.mock
async def test_mentions_use_the_configured_user_and_since_as_start_time():
    _token()
    respx.get("https://api.x.com/2/users/2244994945/mentions").mock(return_value=httpx.Response(200, json={"data": [{"id": "9", "text": "@me hey", "author_id": "5"}], "meta": {"result_count": 1}}))
    res = await _server().call_tool("read_mentions", {"since": "2026-09-01T00:00:00Z"})
    assert res.structured_content["mentions"][0]["text"] == "@me hey"
    params = respx.calls.last.request.url.params
    assert params["start_time"] == "2026-09-01T00:00:00Z" and params["max_results"] == "25"


@pytest.mark.asyncio
@respx.mock
async def test_analytics_returns_public_metrics_and_delete_status():
    _token()
    respx.get("https://api.x.com/2/tweets/1").mock(return_value=httpx.Response(200, json={"data": {"id": "1", "text": "t", "public_metrics": {"repost_count": 1, "reply_count": 2, "like_count": 3, "quote_count": 0, "bookmark_count": 0, "impression_count": 50}}}))
    res = await _server().call_tool("analytics_post", {"post_id": "1"})
    assert res.structured_content["post_id"] == "1" and res.structured_content["metrics"]["like_count"] == 3
    respx.delete("https://api.x.com/2/tweets/1").mock(return_value=httpx.Response(200, json={"data": {"deleted": True}}))
    res = await _server().call_tool("delete", {"post_id": "1"})
    assert res.is_error is False and res.structured_content["status"] == "deleted"


@pytest.mark.asyncio
@respx.mock
async def test_refused_refresh_token_is_an_auth_error_without_secrets():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "invalid_request", "error_description": "Value passed for the token was invalid."}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "REFRESHsecret" not in json.dumps(res.structured_content) and "CLIENTSECRET" not in json.dumps(res.structured_content)
