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

SPEC = json.loads((ROOT / "catalog" / "social" / "weibo.json").read_text(encoding="utf-8"))
B = "https://api.weibo.com/2"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"access_token": "2.00weibo-secret", "user_ip": "211.156.0.1"}, 50, "test"))


@pytest.mark.asyncio
async def test_tools_follow_the_social_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["analytics_post", "delete", "me", "publish_text", "read_comments", "read_mentions"]


@pytest.mark.asyncio
@respx.mock
async def test_publish_text_shares_as_form_with_rip_and_token_query():
    route = respx.post(url__startswith=f"{B}/statuses/share.json").mock(return_value=httpx.Response(200, json={"created_at": "Wed Oct 24 23:49:17 +0800 2012", "id": 3504803600500000, "idstr": "3504803600502730", "text": "hi https://example.com"}))
    res = await _server().call_tool("publish_text", {"text": "hi https://example.com"})
    assert res.is_error is False and res.structured_content["id"] == "3504803600502730"
    req = route.calls.last.request
    assert parse_qs(req.content.decode()) == {"status": ["hi https://example.com"], "rip": ["211.156.0.1"]}
    assert req.url.params["access_token"] == "2.00weibo-secret"


@pytest.mark.asyncio
@respx.mock
async def test_read_comments_maps_comments_and_total():
    route = respx.get(url__startswith=f"{B}/comments/show.json").mock(return_value=httpx.Response(200, json={"comments": [
        {"created_at": "Wed Jun 01 00:50:25 +0800 2011", "id": 12438492184, "idstr": "12438492184", "text": "love your work", "user": {"screen_name": "zaku"}}], "total_number": 7}))
    res = await _server().call_tool("read_comments", {"post_id": "11488058246", "limit": 10})
    sc = res.structured_content
    assert sc["comments"][0]["author"] == "zaku" and sc["total"] == 7
    p = route.calls.last.request.url.params
    assert p["id"] == "11488058246" and p["count"] == "10" and p["page"] == "1"


@pytest.mark.asyncio
@respx.mock
async def test_analytics_reads_the_first_count_row_and_errors_hide_the_token():
    respx.get(url__startswith=f"{B}/statuses/count.json").mock(return_value=httpx.Response(200, json=[{"id": "32817222", "comments": "16", "reposts": "38"}]))
    res = await _server().call_tool("analytics_post", {"post_id": "32817222"})
    assert res.structured_content["reposts"] == "38"
    respx.get(url__startswith=f"{B}/account/get_uid.json").mock(return_value=httpx.Response(403, json={"error": "invalid_access_token 2.00weibo-secret", "error_code": 21332}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "2.00weibo-secret" not in json.dumps(res.structured_content)
