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

SPEC = json.loads((ROOT / "catalog" / "social" / "linkedin.json").read_text(encoding="utf-8"))
L = "https://api.linkedin.com"


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], {"client_id": "cid", "client_secret": "sec", "refresh_token": "AQR", "author_urn": "urn:li:organization:5515715"}, 50, "test")
    t.fixed_headers = a["headers"]
    return build_server(SPEC, transport=t)


def _token():
    return respx.post("https://www.linkedin.com/oauth/v2/accessToken").mock(return_value=httpx.Response(200, json={"access_token": "AQV", "expires_in": 5184000}))


@pytest.mark.asyncio
async def test_tools_and_header_only_publish_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "delete", "me", "read_comments", "read_mentions", "reply_comment"]
    assert "x-restli-id" in SPEC["adapter"]["not_offered"]["publish_text"]


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_with_restli_headers():
    _token()
    respx.get(f"{L}/rest/socialActions/urn:li:share:1/comments").mock(return_value=httpx.Response(200, json={"paging": {"total": 1}, "elements": [
        {"commentUrn": "urn:li:comment:(urn:li:activity:9,8)", "actor": "urn:li:person:A", "message": {"text": "nice"}, "created": {"time": 1582160678569}}]}))
    res = await _server().call_tool("read_comments", {"post_id": "urn:li:share:1", "page": 2, "limit": 10})
    c = res.structured_content["comments"][0]
    assert c["id"] == "urn:li:comment:(urn:li:activity:9,8)" and c["text"] == "nice" and res.structured_content["total"] == 1
    req = respx.calls.last.request
    assert req.url.params["start"] == "10" and req.url.params["count"] == "10"
    assert req.headers["Linkedin-Version"] == "202609" and req.headers["X-Restli-Protocol-Version"] == "2.0.0" and req.headers["Authorization"] == "Bearer AQV"


@pytest.mark.asyncio
@respx.mock
async def test_reply_comment_is_nested_under_the_parent():
    _token()
    route = respx.post(f"{L}/rest/socialActions/urn:li:comment:(urn:li:activity:9,8)/comments").mock(return_value=httpx.Response(201, json={
        "commentUrn": "urn:li:comment:(urn:li:activity:9,7)", "created": {"time": 1583863835990}}))
    res = await _server().call_tool("reply_comment", {"comment_id": "urn:li:comment:(urn:li:activity:9,8)", "text": "thanks"})
    assert res.structured_content["id"] == "urn:li:comment:(urn:li:activity:9,7)"
    assert json.loads(route.calls.last.request.content) == {"actor": "urn:li:organization:5515715", "message": {"text": "thanks"}, "parentComment": "urn:li:comment:(urn:li:activity:9,8)"}


@pytest.mark.asyncio
@respx.mock
async def test_mentions_delete_and_social_metadata():
    _token()
    respx.get(url__startswith=f"{L}/rest/organizationalEntityNotifications").mock(return_value=httpx.Response(200, json={"elements": [{"notificationId": 4406044, "lastModifiedAt": 1535741320050, "action": "SHARE_MENTION"}]}))
    res = await _server().call_tool("read_mentions", {})
    assert res.structured_content["mentions"][0]["id"] == "4406044"
    url = str(respx.calls.last.request.url)
    assert "q=criteria&actions=List(SHARE_MENTION)" in url and "organizationalEntity=urn%3Ali%3Aorganization%3A5515715" in url
    d = respx.delete(f"{L}/rest/posts/urn%3Ali%3Ashare%3A1").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("delete", {"post_id": "urn%3Ali%3Ashare%3A1"})
    assert res.structured_content["status"] == "deleted" and d.calls.last.request.headers["X-RestLi-Method"] == "DELETE"
    respx.get(f"{L}/rest/socialMetadata/urn:li:share:1").mock(return_value=httpx.Response(200, json={"entity": "urn:li:activity:6", "commentSummary": {"count": 4}}))
    res = await _server().call_tool("analytics_post", {"post_id": "urn:li:share:1"})
    assert res.structured_content["post_id"] == "urn:li:activity:6" and res.structured_content["metrics"]["commentSummary"]["count"] == 4
