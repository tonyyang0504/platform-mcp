import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "builder_tools" / "wordpress.json").read_text(encoding="utf-8"))
CREDS = {'username': 'editor', 'application_password': 'abcd efgh ijkl', 'site': 'blog.example.com'}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], CREDS, 50, "test", envelope=a.get("envelope"))
    return build_server(SPEC, transport=t)


def _q(req):
    return {k: v[0] for k, v in parse_qs(urlparse(str(req.url)).query).items()}


def _body(req):
    return json.loads(req.content)


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {'update_item', 'create_item', 'me', 'delete_item', 'list_items', 'get_item'}


import base64

B = "https://blog.example.com/wp-json/wp/v2"


@pytest.mark.asyncio
@respx.mock
async def test_list_posts_basic_auth_and_paging():
    route = respx.get(f"{B}/posts").mock(return_value=httpx.Response(200, json=[{"id": 1, "title": {"raw": "Hello", "rendered": "Hello"}, "link": "https://blog.example.com/hello", "modified_gmt": "2026-09-01T00:00:00", "status": "publish"}]))
    res = await _server().call_tool("list_items", {"query": "hel", "page": 2, "limit": 5})
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(b"editor:abcd efgh ijkl").decode()
    assert _q(req) == {"page": "2", "per_page": "5", "search": "hel", "status": "any", "context": "edit"}
    assert res.structured_content["items"][0]["title"] == "Hello"


@pytest.mark.asyncio
@respx.mock
async def test_create_page_draft_body():
    route = respx.post(f"{B}/pages").mock(return_value=httpx.Response(201, json={"id": 44, "link": "https://blog.example.com/?page_id=44", "status": "draft"}))
    res = await _server().call_tool("create_item", {"collection": "pages", "title": "About", "content": "<p>Hi</p>", "fields": {"status": "draft", "slug": "about"}})
    assert _body(route.calls[0].request) == {"title": "About", "content": "<p>Hi</p>", "status": "draft", "slug": "about"}
    assert (res.structured_content["id"], res.structured_content["status"]) == ("44", "draft")


@pytest.mark.asyncio
@respx.mock
async def test_get_update_trash():
    respx.get(f"{B}/posts/1").mock(return_value=httpx.Response(200, json={"id": 1, "title": {"raw": "T"}, "content": {"raw": "<!-- wp:paragraph -->"}}))
    up = respx.post(f"{B}/posts/1").mock(return_value=httpx.Response(200, json={"id": 1, "status": "publish"}))
    respx.delete(f"{B}/posts/1").mock(return_value=httpx.Response(200, json={"id": 1, "status": "trash"}))
    res = await _server().call_tool("get_item", {"item_id": "1"})
    assert res.structured_content["content"] == "<!-- wp:paragraph -->"
    await _server().call_tool("update_item", {"item_id": "1", "fields": {"status": "publish"}})
    assert _body(up.calls[0].request) == {"status": "publish"}
    res = await _server().call_tool("delete_item", {"item_id": "1"})
    assert res.structured_content["status"] == "trash"
