"""Facebook Pages API: Page token as bearer, page_id config field."""
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

SPEC = json.loads((ROOT / "catalog" / "social" / "facebook.json").read_text(encoding="utf-8"))
G = "https://graph.facebook.com/v26.0"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"page_access_token": "PAGE-TOKEN", "page_id": "1234"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_cover_the_whole_social_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "delete", "me", "publish_image", "publish_text", "read_comments", "read_mentions", "reply_comment"]
    assert SPEC["adapter"]["not_offered"] == {}
    assert next(t for t in tools if t.name == "delete").annotations.destructive_hint is True


@pytest.mark.asyncio
@respx.mock
async def test_publish_text_posts_to_the_page_feed_with_the_page_token():
    # developers.facebook.com/docs/pages-api/posts -> {"id": "page_post_id"}
    route = respx.post(f"{G}/1234/feed").mock(return_value=httpx.Response(200, json={"id": "1234_5678"}))
    res = await _server().call_tool("publish_text", {"text": "hello page", "reply_to": "ignored"})
    assert res.is_error is False and res.structured_content["id"] == "1234_5678"
    req = route.calls.last.request
    assert json.loads(req.content) == {"message": "hello page"} and req.headers["Authorization"] == "Bearer PAGE-TOKEN"


@pytest.mark.asyncio
@respx.mock
async def test_publish_image_uses_the_first_url_and_returns_the_post_id():
    route = respx.post(f"{G}/1234/photos").mock(return_value=httpx.Response(200, json={"id": "999", "post_id": "1234_777"}))
    res = await _server().call_tool("publish_image", {"text": "cap", "image_urls": ["https://img.example/a.jpg", "https://img.example/b.jpg"]})
    assert res.is_error is False and res.structured_content["id"] == "1234_777" and res.structured_content["photo_id"] == "999"
    assert json.loads(route.calls.last.request.content) == {"url": "https://img.example/a.jpg", "caption": "cap"}


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_maps_from_and_summary_total():
    respx.get(f"{G}/1234_5678/comments").mock(return_value=httpx.Response(200, json={
        "data": [{"created_time": "2020-02-19T23:05:53+0000", "from": {"name": "Ann", "id": "42"}, "message": "nice", "id": "5678_1"}],
        "paging": {"cursors": {"before": "MQZDZD", "after": "MQZDZD"}}, "summary": {"order": "chronological", "total_count": 1}}))
    res = await _server().call_tool("read_comments", {"post_id": "1234_5678", "limit": 10})
    c = res.structured_content["comments"][0]
    assert c["id"] == "5678_1" and c["author"] == "Ann" and c["text"] == "nice" and res.structured_content["total"] == 1
    params = respx.calls.last.request.url.params
    assert params["fields"] == "id,from,message,created_time" and params["summary"] == "true" and params["limit"] == "10"


@pytest.mark.asyncio
@respx.mock
async def test_analytics_reads_counts_and_expired_token_is_auth_error():
    respx.get(f"{G}/1234_5678").mock(return_value=httpx.Response(200, json={
        "id": "1234_5678", "permalink_url": "https://www.facebook.com/1234_5678", "shares": {"count": 3},
        "comments": {"data": [], "summary": {"total_count": 7}}, "reactions": {"data": [], "summary": {"total_count": 11}}}))
    res = await _server().call_tool("analytics_post", {"post_id": "1234_5678"})
    sc = res.structured_content
    assert sc["post_id"] == "1234_5678" and sc["shares"] == 3 and sc["comments"] == 7 and sc["reactions"] == 11
    respx.delete(f"{G}/1234_9").mock(return_value=httpx.Response(401, json={"error": {"message": "Error validating access token", "code": 190}}))
    res = await _server().call_tool("delete", {"post_id": "1234_9"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
