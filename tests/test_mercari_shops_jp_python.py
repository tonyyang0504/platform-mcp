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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "mercari_shops_jp.json").read_text(encoding="utf-8"))
URL = "https://api.mercari-shops-sandbox.com/v1/graphql"
CREDS = {"access_token": "PAT-secret-0123456789", "api_host": "api.mercari-shops-sandbox.com", "user_agent": "EXAMPLE_SHOP/1.0.0"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a["envelope"]))


@pytest.mark.asyncio
@respx.mock
async def test_me_posts_shop_query_with_bearer_and_contract_user_agent():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"data": {"shop": {"id": "4", "name": "shop", "shopStatus": "OPENED"}}}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]
    res = await server.call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["data"]["shop"]["name"] == "shop"
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer PAT-secret-0123456789" and req.headers["User-Agent"] == "EXAMPLE_SHOP/1.0.0"
    assert json.loads(req.content)["query"].startswith("query shop")


@pytest.mark.asyncio
@respx.mock
async def test_update_listing_sends_variables_and_maps_status():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"data": {"updateProduct": {"product": {"id": "p1", "status": "OPENED", "price": 1500}}}}))
    res = await _server().call_tool("update_listing", {"listing_id": "p1", "price": 1500, "title": "Tシャツ"})
    assert res.is_error is False and res.structured_content["status"] == "OPENED"
    body = json.loads(route.calls.last.request.content)
    assert body["variables"] == {"input": {"id": "p1", "name": "Tシャツ", "price": 1500}} and "updateProduct" in body["query"]


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_reads_connection_edges():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"data": {"orderTransactions": {"edges": [
        {"node": {"id": "ot1", "status": "WAITING_FOR_SHIPPING", "totalPrice": 3300, "createdAt": "2026-09-20T10:00:00Z"}}], "pageInfo": {"endCursor": "c1", "hasNextPage": False}}}}))
    res = await _server().call_tool("list_orders", {"status": "WAITING_FOR_SHIPPING", "since": "2026-09-01T00:00:00Z", "limit": 20})
    o = res.structured_content["orders"][0]
    assert o["id"] == "ot1" and o["total"] == 3300 and o["currency"] == "JPY" and o["status"] == "WAITING_FOR_SHIPPING"
    assert json.loads(route.calls.last.request.content)["variables"] == {"first": 20, "orderedDateGte": "2026-09-01T00:00:00Z", "statuses": ["WAITING_FOR_SHIPPING"]}


@pytest.mark.asyncio
@respx.mock
async def test_graphql_errors_are_errors():
    respx.post(URL).mock(return_value=httpx.Response(200, json={"errors": [{"message": "variant not found", "extensions": {"code": "NOT_FOUND"}}], "data": None}))
    res = await _server().call_tool("set_inventory", {"sku": "SKU-1", "quantity": 3})
    assert res.is_error is True and "variant not found" in res.structured_content["message"]
