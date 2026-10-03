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

SPEC = json.loads((ROOT / "catalog" / "builder_tools" / "webflow.json").read_text(encoding="utf-8"))
CREDS = {'token': 'wf-secret'}


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


B = "https://api.webflow.com/v2"


@pytest.mark.asyncio
@respx.mock
async def test_list_items_offset_total():
    route = respx.get(f"{B}/collections/c1/items").mock(return_value=httpx.Response(200, json={"items": [{"id": "i1", "lastUpdated": "2026-09-01", "fieldData": {"name": "Post", "slug": "post"}}], "pagination": {"limit": 10, "offset": 10, "total": 11}}))
    res = await _server().call_tool("list_items", {"collection": "c1", "page": 2, "limit": 10})
    assert route.calls[0].request.headers["Authorization"] == "Bearer wf-secret"
    assert _q(route.calls[0].request) == {"offset": "10", "limit": "10"}
    sc = res.structured_content
    assert (sc["items"][0]["title"], sc["items"][0]["url"], sc["total"], sc["next_page"]) == ("Post", "post", 11, None)


@pytest.mark.asyncio
@respx.mock
async def test_create_item_field_data():
    route = respx.post(f"{B}/collections/c1/items").mock(return_value=httpx.Response(202, json={"id": "i2", "isDraft": False, "fieldData": {"name": "Hello", "slug": "hello"}}))
    res = await _server().call_tool("create_item", {"collection": "c1", "title": "Hello", "fields": {"slug": "hello", "post-body": "<p>x</p>"}})
    assert _body(route.calls[0].request) == {"fieldData": {"slug": "hello", "post-body": "<p>x</p>", "name": "Hello"}}
    assert res.structured_content["id"] == "i2"


@pytest.mark.asyncio
@respx.mock
async def test_update_delete_and_missing_collection():
    up = respx.patch(f"{B}/collections/c1/items/i2").mock(return_value=httpx.Response(200, json={"id": "i2"}))
    respx.delete(f"{B}/collections/c1/items/i2").mock(return_value=httpx.Response(204))
    await _server().call_tool("update_item", {"collection": "c1", "item_id": "i2", "title": "Hi"})
    assert _body(up.calls[0].request) == {"fieldData": {"name": "Hi"}}
    res = await _server().call_tool("delete_item", {"collection": "c1", "item_id": "i2"})
    assert res.structured_content["status"] == "deleted"
    res = await _server().call_tool("list_items", {})
    assert res.structured_content["error"] == "invalid_input"
