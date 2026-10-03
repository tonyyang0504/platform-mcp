"""Instagram API with Facebook Login: comments, replies, tags, media counts."""
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

SPEC = json.loads((ROOT / "catalog" / "social" / "instagram.json").read_text(encoding="utf-8"))
G = "https://graph.facebook.com/v26.0"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"access_token": "IG-TOKEN", "ig_user_id": "17841405822304914"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_two_step_publishing_and_delete_are_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "me", "read_comments", "read_mentions", "reply_comment"]
    assert set(SPEC["adapter"]["not_offered"]) == {"publish_text", "publish_image", "delete"}
    assert "media_publish" in SPEC["adapter"]["not_offered"]["publish_image"]


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_maps_the_documented_shape():
    respx.get(f"{G}/17895695668004550/comments").mock(return_value=httpx.Response(200, json={"data": [
        {"timestamp": "2017-08-31T19:16:02+0000", "text": "This is awesome!", "id": "17870913679156914", "username": "fan1"}]}))
    res = await _server().call_tool("read_comments", {"post_id": "17895695668004550"})
    c = res.structured_content["comments"][0]
    assert c["id"] == "17870913679156914" and c["author"] == "fan1" and c["text"] == "This is awesome!"
    req = respx.calls.last.request
    assert req.url.params["fields"] == "id,text,timestamp,username,from" and "limit" not in req.url.params and req.headers["Authorization"] == "Bearer IG-TOKEN"


@pytest.mark.asyncio
@respx.mock
async def test_reply_comment_posts_to_replies():
    route = respx.post(f"{G}/17870913679156914/replies").mock(return_value=httpx.Response(200, json={"id": "17873440459141029"}))
    res = await _server().call_tool("reply_comment", {"comment_id": "17870913679156914", "text": "Thanks for sharing!"})
    assert res.is_error is False and res.structured_content["id"] == "17873440459141029"
    assert json.loads(route.calls.last.request.content) == {"message": "Thanks for sharing!"}


@pytest.mark.asyncio
@respx.mock
async def test_read_mentions_uses_tags_with_posted_after_and_analytics_reads_counts():
    respx.get(f"{G}/17841405822304914/tags").mock(return_value=httpx.Response(200, json={"data": [{"id": "18038", "username": "keldo", "caption": "hi @me", "timestamp": "2026-09-20T10:00:00+0000"}]}))
    res = await _server().call_tool("read_mentions", {"since": "2026-09-01T00:00:00"})
    m = res.structured_content["mentions"][0]
    assert m["id"] == "18038" and m["author"] == "keldo" and m["text"] == "hi @me"
    assert respx.calls.last.request.url.params["posted_after"] == "2026-09-01T00:00:00"
    respx.get(f"{G}/18038").mock(return_value=httpx.Response(200, json={"id": "18038", "like_count": 5, "comments_count": 2, "permalink": "https://www.instagram.com/p/x/"}))
    res = await _server().call_tool("analytics_post", {"post_id": "18038"})
    assert res.structured_content["post_id"] == "18038" and res.structured_content["likes"] == 5 and res.structured_content["comments"] == 2
