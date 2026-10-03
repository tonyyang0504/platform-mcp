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

SPEC = json.loads((ROOT / "catalog" / "social" / "vimeo.json").read_text(encoding="utf-8"))


def _server():
    a = SPEC["adapter"]
    s = build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"access_token": "vimeo-secret-token"}, 50, "test"))
    return s


@pytest.mark.asyncio
async def test_tools_follow_the_social_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "delete", "me", "read_comments"]


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_pages_and_sends_the_versioned_accept_header():
    route = respx.get("https://api.vimeo.com/videos/258684937/comments").mock(return_value=httpx.Response(200, json={
        "total": 14, "page": 2, "per_page": 5, "paging": {}, "data": [{"uri": "/videos/258684937/comments/12345", "text": "Great!", "created_on": "2026-09-01T10:00:00+00:00", "user": {"name": "Ann"}}]}))
    res = await _server().call_tool("read_comments", {"post_id": "258684937", "page": 2, "limit": 5})
    sc = res.structured_content
    assert sc["total"] == 14 and sc["comments"][0]["id"] == "/videos/258684937/comments/12345" and sc["comments"][0]["author"] == "Ann"
    req = route.calls.last.request
    assert req.url.params["page"] == "2" and req.url.params["per_page"] == "5"
    assert req.headers["Accept"] == "application/vnd.vimeo.*+json;version=3.4" and req.headers["Authorization"] == "Bearer vimeo-secret-token"


@pytest.mark.asyncio
@respx.mock
async def test_delete_answers_204_as_deleted_and_analytics_maps_plays():
    respx.delete("https://api.vimeo.com/videos/1").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("delete", {"post_id": "1"})
    assert res.is_error is False and res.structured_content["status"] == "deleted"
    route = respx.get("https://api.vimeo.com/videos/1").mock(return_value=httpx.Response(200, json={"uri": "/videos/1", "link": "https://vimeo.com/1", "stats": {"plays": 20}, "metadata": {"connections": {"comments": {"total": 3}, "likes": {"total": 9}}}}))
    res = await _server().call_tool("analytics_post", {"post_id": "1"})
    assert res.structured_content["plays"] == 20 and res.structured_content["likes"] == 9
    assert "stats.plays" in route.calls.last.request.url.params["fields"]


@pytest.mark.asyncio
@respx.mock
async def test_forbidden_delete_is_an_auth_error_without_the_token():
    respx.delete("https://api.vimeo.com/videos/2").mock(return_value=httpx.Response(403, json={"error": "no delete scope for vimeo-secret-token"}))
    res = await _server().call_tool("delete", {"post_id": "2"})
    assert res.structured_content["error"] == "auth_error" and "vimeo-secret-token" not in json.dumps(res.structured_content)
