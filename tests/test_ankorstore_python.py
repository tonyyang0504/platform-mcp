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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "ankorstore.json").read_text(encoding="utf-8"))
BASE = "https://www.ankorstore.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "cid", "client_secret": "sek-ret-9"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post(f"{BASE}/oauth/token").mock(return_value=httpx.Response(200, json={"token_type": "Bearer", "expires_in": 3600, "access_token": "AT-1"}))


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_order", "get_product", "list_products", "me", "track"]  # brand API: no purchasing
    assert all(t.annotations.read_only_hint is True for t in tools)


@pytest.mark.asyncio
@respx.mock
async def test_list_products_uses_client_credentials_and_jsonapi():
    tok = _token()
    # ankorstore.github.io/api-docs: GET /api/v1/products -> {meta{page}, data[{type: product, id, attributes{name, wholesalePrice, retailPrice}}]}
    route = respx.get(f"{BASE}/api/v1/products").mock(return_value=httpx.Response(200, json={
        "meta": {"page": {"hasMore": True, "perPage": 2}}, "data": [
            {"type": "product", "id": "0c5e6540-0da9-1ecb-bf59-0242ac170007", "attributes": {"name": "Example Product", "retailPrice": 750, "wholesalePrice": 426, "active": True, "outOfStock": False}}]}))
    res = await _server().call_tool("list_products", {"limit": 80})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "0c5e6540-0da9-1ecb-bf59-0242ac170007" and p["title"] == "Example Product" and p["wholesale_price_cents"] == 426
    form = dict(x.split("=") for x in tok.calls.last.request.content.decode().split("&"))
    assert form["grant_type"] == "client_credentials" and form["client_id"] == "cid" and form["scope"] == "%2A"
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer AT-1" and req.headers["Accept"] == "application/vnd.api+json"
    assert req.url.params["page[limit]"] == "50"


@pytest.mark.asyncio
@respx.mock
async def test_get_order_and_track_read_the_shipping_overview():
    _token()
    order = {"data": {"type": "order", "id": "1ecb023e", "attributes": {"status": "invoiced", "brandCurrency": "EUR", "brandTotalAmountWithVat": 23405, "createdAt": "2022-03-13T16:36:24+00:00",
             "shippingOverview": {"parcels": [{"trackedPackage": {"trackingNumber": "1Z8A76119134110028", "trackingLink": "https://www.ups.com/track?tracknum=1Z8A", "currentStatus": {"status": "DELIVERED", "statusDetails": "Delivered", "updatedAt": "2022-03-21T10:36:46+00:00"}}}]}}}}
    respx.get(f"{BASE}/api/v1/orders/1ecb023e").mock(return_value=httpx.Response(200, json=order))
    s = _server()
    res = await s.call_tool("get_order", {"id": "1ecb023e"})
    sc = res.structured_content
    assert sc["status"] == "invoiced" and sc["total_cents"] == 23405 and sc["currency"] == "EUR" and sc["tracking_number"] == "1Z8A76119134110028"
    tr = await s.call_tool("track", {"order_id": "1ecb023e"})
    assert tr.structured_content["events"][0]["status"] == "DELIVERED"


@pytest.mark.asyncio
@respx.mock
async def test_refused_token_is_an_auth_error_without_the_secret():
    respx.post(f"{BASE}/oauth/token").mock(return_value=httpx.Response(401, json={"error": "invalid_client", "message": "client sek-ret-9 unknown"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "sek-ret-9" not in json.dumps(res.structured_content)
