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

SPEC = json.loads((ROOT / "catalog" / "builder_tools" / "shopify.json").read_text(encoding="utf-8"))
CREDS = {'access_token': 'shpat_secret', 'shop': 'demo-store'}


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


B = "https://demo-store.myshopify.com/admin/api/2026-07"


@pytest.mark.asyncio
@respx.mock
async def test_list_products_graphql_cursor():
    route = respx.post(f"{B}/graphql.json").mock(return_value=httpx.Response(200, json={"data": {"products": {
        "nodes": [{"id": "gid://shopify/Product/1", "legacyResourceId": "1", "title": "Shirt", "status": "ACTIVE", "updatedAt": "2026-09-01T00:00:00Z"}],
        "pageInfo": {"hasNextPage": True, "endCursor": "eyJ"}}}}))
    res = await _server().call_tool("list_items", {"limit": 10, "cursor": "abc", "query": "title:shirt"})
    assert res.is_error is False
    req = route.calls[0].request
    assert req.headers["X-Shopify-Access-Token"] == "shpat_secret"
    b = _body(req)
    assert b["variables"] == {"first": 10, "after": "abc", "query": "title:shirt"} and "products(first: $first" in b["query"]
    assert res.structured_content["items"][0]["id"] == "1" and res.structured_content["next_cursor"] == "eyJ"


@pytest.mark.asyncio
@respx.mock
async def test_create_product_merges_fields():
    route = respx.post(f"{B}/products.json").mock(return_value=httpx.Response(201, json={"product": {"id": 632910392, "status": "draft", "handle": "tee"}}))
    res = await _server().call_tool("create_item", {"title": "Tee", "content": "<p>soft</p>", "fields": {"status": "draft", "vendor": "Acme"}})
    assert _body(route.calls[0].request) == {"product": {"status": "draft", "vendor": "Acme", "title": "Tee", "body_html": "<p>soft</p>"}}
    assert res.structured_content["id"] == "632910392"


@pytest.mark.asyncio
@respx.mock
async def test_get_update_delete_product():
    respx.get(f"{B}/products/5.json").mock(return_value=httpx.Response(200, json={"product": {"id": 5, "title": "Mug", "body_html": "<b>x</b>"}}))
    up = respx.put(f"{B}/products/5.json").mock(return_value=httpx.Response(200, json={"product": {"id": 5, "status": "active"}}))
    respx.delete(f"{B}/products/5.json").mock(return_value=httpx.Response(200, json={}))
    res = await _server().call_tool("get_item", {"item_id": "5"})
    assert (res.structured_content["title"], res.structured_content["content"]) == ("Mug", "<b>x</b>")
    await _server().call_tool("update_item", {"item_id": "5", "title": "Big mug"})
    assert _body(up.calls[0].request) == {"product": {"title": "Big mug"}}
    res = await _server().call_tool("delete_item", {"item_id": "5"})
    assert res.structured_content["status"] == "deleted"
