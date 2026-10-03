import base64
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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "tiki.json").read_text(encoding="utf-8"))
API = "https://api.tiki.vn/integration"
CREDS = {"client_id": "7590139168389961", "client_secret": "tfSl0c6VFv3fAB_z9F", "warehouse_id": "1034"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _token():
    return respx.post("https://api.tiki.vn/sc/oauth2/token").mock(return_value=httpx.Response(200, json={"access_token": "tiki.at", "expires_in": 3599, "token_type": "bearer"}))


@pytest.mark.asyncio
@respx.mock
async def test_basic_client_credentials_and_seller():
    tok = _token()
    respx.get(f"{API}/v2/sellers/me").mock(return_value=httpx.Response(200, json={"id": 5678, "name": "Sushi shop", "active": 1}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]
    assert (await server.call_tool("me", {})).structured_content["account"]["name"] == "Sushi shop"
    assert tok.calls.last.request.headers["Authorization"] == "Basic " + base64.b64encode(b"7590139168389961:tfSl0c6VFv3fAB_z9F").decode()


@pytest.mark.asyncio
@respx.mock
async def test_product_updates():
    _token()
    sku = respx.put(f"{API}/v2/products/updateSku").mock(return_value=httpx.Response(200, json={"state": "approved"}))
    await _server().call_tool("update_listing", {"listing_id": "2166152", "price": 100000})
    assert json.loads(sku.calls.last.request.content) == {"product_id": 2166152, "price": 100000}
    await _server().call_tool("set_inventory", {"sku": "xxx-yyy-123", "quantity": 17})
    assert json.loads(sku.calls.last.request.content) == {"original_sku": "xxx-yyy-123", "warehouse_quantities": [{"warehouse_id": 1034, "qty_available": 17}]}
    batch = respx.put(f"{API}/v2.1/products/updateSkus").mock(return_value=httpx.Response(200, json={}))
    res = await _server().call_tool("end_listing", {"listing_id": "2166152"})
    assert res.structured_content["status"] == "disabled" and json.loads(batch.calls.last.request.content) == {"data": [{"product_id": 2166152, "status": 2}]}


@pytest.mark.asyncio
@respx.mock
async def test_orders_set_expression_status():
    _token()
    route = respx.get(f"{API}/v2/orders").mock(return_value=httpx.Response(200, json={"data": [{"code": "745467462", "status": "queueing", "created_at": "2026-09-20 18:50:17", "invoice": {"grand_total": 455000}}], "paging": {}}))
    res = await _server().call_tool("list_orders", {"status": "nin|processing,waiting_payment", "since": "2026-09-01 00:00:00"})
    o = res.structured_content["orders"][0]
    assert o["id"] == "745467462" and o["total"] == 455000 and o["currency"] == "VND"
    assert route.calls.last.request.url.params["status"] == "nin|processing,waiting_payment"
