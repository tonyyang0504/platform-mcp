"""Reddit: application-only OAuth2 (client_credentials with HTTP Basic client auth) -> read-only calls on oauth.reddit.com."""
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

SPEC = json.loads((ROOT / "catalog" / "social" / "reddit.json").read_text(encoding="utf-8"))
UA = "server:com.example.app:v1.0 (by /u/example)"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "cid", "client_secret": "csec", "user_agent": UA}, 50, f"platform-mcp/reddit {UA}")
    return build_server(SPEC, transport=t)


def _token():
    # github.com/reddit-archive/reddit/wiki/OAuth2 "Application Only OAuth" -> {access_token, token_type, expires_in, scope}
    return respx.post("https://www.reddit.com/api/v1/access_token").mock(
        return_value=httpx.Response(200, json={"access_token": "AT1", "token_type": "bearer", "expires_in": 3600, "scope": "*"}))


@pytest.mark.asyncio
async def test_only_read_tools_are_offered_with_an_app_only_token():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "read_comments"]
    assert all(t.annotations.read_only_hint is True for t in tools)
    assert SPEC["adapter"]["user_agent_field"] == "user_agent"


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_exchanges_client_credentials_then_maps_the_second_listing():
    tok = _token()
    # GET /comments/{article}: [Listing(link), Listing(comments)]; comment fields per reddit-archive/reddit/wiki/JSON
    route = respx.get("https://oauth.reddit.com/comments/1abc23").mock(return_value=httpx.Response(200, json=[
        {"kind": "Listing", "data": {"children": [{"kind": "t3", "data": {"id": "1abc23", "name": "t3_1abc23", "title": "A post"}}]}},
        {"kind": "Listing", "data": {"after": None, "children": [
            {"kind": "t1", "data": {"id": "k9x1", "name": "t1_k9x1", "author": "someone", "body": "first!", "created_utc": 1758708000.0, "score": 12, "parent_id": "t3_1abc23", "link_id": "t3_1abc23"}},
            {"kind": "more", "data": {"id": "k9x9", "name": "t1_k9x9", "count": 3, "children": ["k9x9"]}}]}}]))
    res = await _server().call_tool("read_comments", {"post_id": "1abc23", "limit": 50})
    assert res.is_error is False
    c = res.structured_content["comments"][0]
    assert c["id"] == "k9x1" and c["author"] == "someone" and c["text"] == "first!" and "created_at" not in c and c["raw"]["data"]["created_utc"] == 1758708000.0
    assert res.structured_content["comments"][1]["id"] == "k9x9" and res.structured_content["comments"][1]["author"] is None
    assert res.structured_content["next_page"] is None
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer AT1" and req.url.params["limit"] == "50" and "page" not in req.url.params
    assert req.headers["User-Agent"].endswith(UA)
    treq = tok.calls.last.request
    assert treq.headers["Authorization"].startswith("Basic ") and b"grant_type=client_credentials" in treq.content and treq.headers["User-Agent"].endswith(UA)


@pytest.mark.asyncio
@respx.mock
async def test_analytics_post_reads_the_link_from_api_info_by_fullname():
    _token()
    respx.get("https://oauth.reddit.com/api/info").mock(return_value=httpx.Response(200, json={"kind": "Listing", "data": {"children": [
        {"kind": "t3", "data": {"id": "1abc23", "name": "t3_1abc23", "score": 41, "ups": 41, "downs": 0, "num_comments": 7, "permalink": "/r/test/comments/1abc23/a_post/", "title": "A post"}}]}}))
    res = await _server().call_tool("analytics_post", {"post_id": "t3_1abc23"})
    sc = res.structured_content
    assert res.is_error is False and sc["post_id"] == "t3_1abc23" and sc["score"] == 41 and sc["num_comments"] == 7 and sc["permalink"].startswith("/r/test/")
    assert respx.calls.last.request.url.params["id"] == "t3_1abc23"


@pytest.mark.asyncio
@respx.mock
async def test_rejected_client_secret_is_an_auth_error_result():
    respx.post("https://www.reddit.com/api/v1/access_token").mock(return_value=httpx.Response(401, json={"error": 401, "message": "Unauthorized"}))
    res = await _server().call_tool("read_comments", {"post_id": "1abc23"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
    assert "csec" not in json.dumps(res.structured_content)
