"""Tumblr: API-key level only (api_key query parameter, configured blog); everything at the OAuth level is not offered."""
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

SPEC = json.loads((ROOT / "catalog" / "social" / "tumblr.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "consumer-key", "blog_identifier": "staff.tumblr.com"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_the_api_key_level_verbs_are_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "me"]
    ap = next(t for t in tools if t.name == "analytics_post")
    assert ap.annotations.read_only_hint is True and ap.input_schema["required"] == ["post_id"]
    assert set(SPEC["adapter"]["not_offered"]) == {"publish_text", "publish_image", "read_comments", "reply_comment", "read_mentions", "delete"}
    assert all("OAuth" in reason for reason in SPEC["adapter"]["not_offered"].values())


@pytest.mark.asyncio
@respx.mock
async def test_analytics_post_reads_one_post_by_id_with_the_api_key_in_the_query():
    # tumblr.com/docs/en/api/v2#posts--retrieve-published-posts -> {meta, response{blog, posts[], total_posts}}
    respx.get("https://api.tumblr.com/v2/blog/staff.tumblr.com/posts").mock(return_value=httpx.Response(200, json={
        "meta": {"status": 200, "msg": "OK"},
        "response": {"blog": {"name": "staff", "title": "Tumblr Staff"}, "posts": [
            {"type": "text", "blog_name": "staff", "id": 1234567890, "id_string": "1234567890", "post_url": "https://staff.tumblr.com/post/1234567890",
             "date": "2026-09-24 09:00:00 GMT", "timestamp": 1758704400, "note_count": 321, "tags": ["news"]}], "total_posts": 1}}))
    res = await _server().call_tool("analytics_post", {"post_id": "1234567890"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["post_id"] == "1234567890" and sc["notes"] == 321 and sc["url"] == "https://staff.tumblr.com/post/1234567890" and sc["type"] == "text"
    params = respx.calls.last.request.url.params
    assert params["id"] == "1234567890" and params["api_key"] == "consumer-key"
    assert "Authorization" not in respx.calls.last.request.headers


@pytest.mark.asyncio
@respx.mock
async def test_me_describes_the_configured_blog():
    respx.get("https://api.tumblr.com/v2/blog/staff.tumblr.com/info").mock(return_value=httpx.Response(200, json={
        "meta": {"status": 200, "msg": "OK"}, "response": {"blog": {"title": "Tumblr Staff", "name": "staff", "posts": 5000, "url": "https://staff.tumblr.com/", "uuid": "t:0aY0xL2Fi1OFJg4YxpmegQ"}}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["ok"] is True and res.structured_content["account"]["response"]["blog"]["name"] == "staff"
    assert respx.calls.last.request.url.params["api_key"] == "consumer-key"


@pytest.mark.asyncio
@respx.mock
async def test_unknown_post_is_not_found_and_a_bad_key_is_an_auth_error():
    respx.get("https://api.tumblr.com/v2/blog/staff.tumblr.com/posts").mock(return_value=httpx.Response(404, json={"meta": {"status": 404, "msg": "Not Found"}, "response": []}))
    res = await _server().call_tool("analytics_post", {"post_id": "0"})
    assert res.is_error is True and res.structured_content["error"] == "not_found" and res.structured_content["http_status"] == 404
    respx.get("https://api.tumblr.com/v2/blog/staff.tumblr.com/info").mock(return_value=httpx.Response(401, json={"meta": {"status": 401, "msg": "Unauthorized"}, "response": []}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and "consumer-key" not in json.dumps(res.structured_content)
