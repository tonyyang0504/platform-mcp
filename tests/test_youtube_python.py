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

SPEC = json.loads((ROOT / "catalog" / "social" / "youtube.json").read_text(encoding="utf-8"))
Y = "https://www.googleapis.com/youtube/v3"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"client_id": "c", "client_secret": "s", "refresh_token": "r"}, 50, "test"))


def _token():
    return respx.post("https://oauth2.googleapis.com/token").mock(return_value=httpx.Response(200, json={"access_token": "ya29.Y", "expires_in": 3599}))


@pytest.mark.asyncio
async def test_tools_follow_the_social_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "delete", "me", "read_comments", "reply_comment"]
    assert set(SPEC["adapter"]["not_offered"]) == {"publish_text", "publish_image", "read_mentions"}


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_maps_top_level_comments():
    _token()
    respx.get(f"{Y}/commentThreads").mock(return_value=httpx.Response(200, json={"pageInfo": {"totalResults": 1}, "items": [
        {"id": "Ug1", "snippet": {"topLevelComment": {"id": "Ug1", "snippet": {"authorDisplayName": "Ann", "textDisplay": "nice", "publishedAt": "2026-09-01T00:00:00Z"}}}}]}))
    res = await _server().call_tool("read_comments", {"post_id": "vid1", "limit": 5})
    c = res.structured_content["comments"][0]
    assert c == {**c, "id": "Ug1", "author": "Ann", "text": "nice"}
    q = respx.calls.last.request.url.params
    assert q["videoId"] == "vid1" and q["part"] == "snippet" and q["maxResults"] == "5"


@pytest.mark.asyncio
@respx.mock
async def test_reply_comment_posts_parent_id():
    _token()
    route = respx.post(f"{Y}/comments").mock(return_value=httpx.Response(200, json={"id": "Ug1.r1", "snippet": {"publishedAt": "2026-09-24T00:00:00Z"}}))
    res = await _server().call_tool("reply_comment", {"comment_id": "Ug1", "text": "thanks"})
    assert res.structured_content["id"] == "Ug1.r1"
    assert json.loads(route.calls.last.request.content) == {"snippet": {"parentId": "Ug1", "textOriginal": "thanks"}}


@pytest.mark.asyncio
@respx.mock
async def test_analytics_and_delete():
    _token()
    respx.get(f"{Y}/videos").mock(return_value=httpx.Response(200, json={"items": [{"id": "vid1", "statistics": {"viewCount": "10"}}]}))
    res = await _server().call_tool("analytics_post", {"post_id": "vid1"})
    assert res.structured_content["metrics"] == {"viewCount": "10"}
    respx.delete(f"{Y}/videos").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("delete", {"post_id": "vid1"})
    assert res.structured_content["status"] == "deleted" and respx.calls.last.request.url.params["id"] == "vid1"
    respx.get(f"{Y}/videos").mock(return_value=httpx.Response(200, json={"items": []}))
    res = await _server().call_tool("analytics_post", {"post_id": "nope"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"
