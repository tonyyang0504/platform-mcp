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

SPEC = json.loads((ROOT / "catalog" / "social" / "producthunt.json").read_text(encoding="utf-8"))
G = "https://api.producthunt.com/v2/api/graphql"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"token": "ph-dev-token-123"}, 50, "test", envelope=a["envelope"]))


@pytest.mark.asyncio
async def test_tools_are_read_only():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "me", "read_comments"]
    assert all(t.annotations.read_only_hint for t in tools)


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_maps_comment_edges():
    route = respx.post(G).mock(return_value=httpx.Response(200, json={"data": {"post": {"comments": {"totalCount": 5, "edges": [
        {"node": {"id": "c1", "body": "Congrats!", "createdAt": "2026-09-20T08:00:00Z", "url": "https://www.producthunt.com/posts/x?comment=c1", "user": {"username": "kate"}}}]}}}}))
    res = await _server().call_tool("read_comments", {"post_id": "123", "limit": 5})
    sc = res.structured_content
    assert sc["total"] == 5 and sc["comments"][0]["author"] == "kate" and sc["comments"][0]["text"] == "Congrats!"
    req = route.calls.last.request
    assert json.loads(req.content)["variables"] == {"id": "123", "first": 5} and req.headers["Authorization"] == "Bearer ph-dev-token-123"


@pytest.mark.asyncio
@respx.mock
async def test_analytics_post_maps_counts():
    respx.post(G).mock(return_value=httpx.Response(200, json={"data": {"post": {"id": "123", "name": "X", "url": "https://www.producthunt.com/posts/x", "votesCount": 410, "commentsCount": 52, "reviewsRating": 4.8, "featuredAt": "2026-09-20T07:01:00Z"}}}))
    res = await _server().call_tool("analytics_post", {"post_id": "123"})
    assert res.structured_content["votes"] == 410 and res.structured_content["comments"] == 52


@pytest.mark.asyncio
@respx.mock
async def test_graphql_error_and_401_do_not_leak_the_token():
    respx.post(G).mock(return_value=httpx.Response(200, json={"data": None, "errors": [{"message": "invalid_oauth_token"}]}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True
    respx.post(G).mock(return_value=httpx.Response(401, json={"error": "invalid token ph-dev-token-123"}))
    res = await _server().call_tool("analytics_post", {"post_id": "1"})
    assert res.structured_content["error"] == "auth_error" and "ph-dev-token-123" not in json.dumps(res.structured_content)
