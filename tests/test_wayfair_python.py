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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "wayfair.json").read_text(encoding="utf-8"))
GQL = "https://api.wayfair.com/v1/graphql"
TOKEN = "https://sso.auth.wayfair.com/oauth/token"
CREDS = {"client_id": "wf_cid", "client_secret": "wf_secret_91c2", "supplier_id": "199492"}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test")
    t.fixed_headers = a["headers"]
    return build_server(SPEC, transport=t)


def _token():
    return respx.post(TOKEN).mock(return_value=httpx.Response(200, json={"access_token": "wf_at_77", "expires_in": 86400, "token_type": "Bearer"}))


@pytest.mark.asyncio
@respx.mock
async def test_token_json_body_and_probe():
    tok = _token()
    gql = respx.post(GQL).mock(return_value=httpx.Response(200, json={"data": {"getDropshipPurchaseOrders": []}}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "me", "set_inventory"]
    assert (await server.call_tool("me", {})).is_error is False
    assert json.loads(tok.calls.last.request.content) == {"grant_type": "client_credentials", "audience": "https://api.wayfair.com/", "client_id": "wf_cid", "client_secret": "wf_secret_91c2"}
    req = gql.calls.last.request
    assert req.headers["Authorization"] == "Bearer wf_at_77"
    assert json.loads(req.content)["variables"] == {"limit": 1}


@pytest.mark.asyncio
@respx.mock
async def test_list_open_orders():
    _token()
    gql = respx.post(GQL).mock(return_value=httpx.Response(200, json={"data": {"getDropshipPurchaseOrders": [
        {"poNumber": "CS11111111", "poDate": "2026-09-20 10:00:00.000000 -04:00", "supplierId": 199492, "products": [{"partNumber": "ABC1", "quantity": 1, "price": 17.07}]}]}}))
    res = await _server().call_tool("list_orders", {"status": "open", "since": "2026-09-01T00:00:00Z", "limit": 50})
    o = res.structured_content["orders"][0]
    assert o["id"] == "CS11111111" and o["created_at"].startswith("2026-09-20")
    v = json.loads(gql.calls.last.request.content)["variables"]
    assert v == {"limit": 25, "hasResponse": False, "fromDate": "2026-09-01T00:00:00Z", "sortOrder": "ASC"}
    bad = await _server().call_tool("list_orders", {"status": "shipped"})
    assert bad.is_error is True


@pytest.mark.asyncio
@respx.mock
async def test_inventory_and_discontinue():
    _token()
    gql = respx.post(GQL).mock(return_value=httpx.Response(200, json={"data": {"inventory": {"save": {"handle": "h1", "status": "PROCESSING", "itemCount": 1, "errorCount": 0, "errors": []}}}}))
    res = await _server().call_tool("set_inventory", {"sku": "PART-A", "quantity": 12})
    assert res.structured_content["status"] == "PROCESSING"
    body = json.loads(gql.calls.last.request.content)
    assert body["variables"] == {"inventory": [{"supplierId": 199492, "supplierPartNumber": "PART-A", "quantityOnHand": 12}], "feedKind": "DIFFERENTIAL"}
    assert body["query"].startswith("mutation saveInventory")
    await _server().call_tool("end_listing", {"listing_id": "PART-B"})
    line = json.loads(gql.calls.last.request.content)["variables"]["inventory"][0]
    assert line == {"supplierId": 199492, "supplierPartNumber": "PART-B", "quantityOnHand": 0, "discontinued": True}
