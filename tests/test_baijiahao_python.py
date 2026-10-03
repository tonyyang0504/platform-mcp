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

SPEC = json.loads((ROOT / "catalog" / "social" / "baijiahao.json").read_text(encoding="utf-8"))
BASE = "https://baijiahao.baidu.com/builderinner/open/resource"
CREDS = {"app_id": "1111111111", "app_token": "tok-secret"}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope"))
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
@respx.mock
async def test_tools_and_read_comments():
    route = respx.post(f"{BASE}/query/articleCommentList").mock(return_value=httpx.Response(200, json={
        "errno": 0, "errmsg": "成功", "data": {"page": {"page_no": 1, "page_size": 20, "has_next": False, "items_count": 1},
        "items": {"article_id": "111", "nid": "112", "total": 1, "reply_list": [
            {"reply_id": "11111111111111114", "uname": "评论者", "content": "写得好", "create_time": 1562829148}]}}}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["analytics_post", "delete", "me", "read_comments"]
    res = await server.call_tool("read_comments", {"post_id": "111", "limit": 20})
    c = res.structured_content["comments"][0]
    assert c["id"] == "11111111111111114" and c["author"] == "评论者" and c["text"] == "写得好"
    body = json.loads(route.calls.last.request.content)
    assert body == {"app_id": CREDS["app_id"], "app_token": CREDS["app_token"], "article_id": "111", "page_no": 1, "page_size": 20}


@pytest.mark.asyncio
@respx.mock
async def test_analytics_post_counts():
    respx.post(f"{BASE}/query/articleStatistics").mock(return_value=httpx.Response(200, json={
        "errno": 0, "errmsg": "成功", "data": {"recommend_count": 5359665, "comment_count": 1004, "view_count": 307033,
                                              "share_count": 486, "collect_count": 701, "likes_count": 715}}))
    out = (await _server().call_tool("analytics_post", {"post_id": "111"})).structured_content
    assert out["views"] == 307033 and out["likes"] == 715 and out["comments"] == 1004 and out["raw"]["share_count"] == 486


@pytest.mark.asyncio
@respx.mock
async def test_delete_withdraws_and_me_probe():
    w = respx.post(f"{BASE}/article/withdraw").mock(return_value=httpx.Response(200, json={"errno": 0, "errmsg": "成功", "data": {"article_id": "999"}}))
    out = (await _server().call_tool("delete", {"post_id": "999"})).structured_content
    assert out["status"] == "withdrawn" and json.loads(w.calls.last.request.content)["article_id"] == "999"
    m = respx.post(f"{BASE}/query/articleListall").mock(return_value=httpx.Response(200, json={"errno": 0, "errmsg": "成功", "data": {"page": {}, "items": {}}}))
    me = await _server().call_tool("me", {})
    assert me.is_error is False and json.loads(m.calls.last.request.content)["page_size"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_errno_envelope_is_error():
    respx.post(f"{BASE}/query/articleStatistics").mock(return_value=httpx.Response(200, json={"data": None, "errno": 60001001, "errmsg": "授权校验失败"}))
    bad = await _server().call_tool("analytics_post", {"post_id": "1"})
    assert bad.is_error is True and "授权校验失败" in bad.content[0].text
