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

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "mercado_libre.json").read_text(encoding="utf-8"))
CREDS = {"client_id": "123", "client_secret": "ml-client-secret", "refresh_token": "TG-ml-refresh-1", "seller_id": "999"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _token():
    return respx.post("https://api.mercadolibre.com/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "APP_USR-ml-access", "expires_in": 21600, "refresh_token": "TG-ml-refresh-2"}))


@pytest.mark.asyncio
async def test_tools_follow_the_marketplaces_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_product", "list_sales", "me", "update_price"]


@pytest.mark.asyncio
@respx.mock
async def test_update_price_puts_only_the_price_and_maps_the_item():
    _token()
    route = respx.put("https://api.mercadolibre.com/items/MLB12345678").mock(return_value=httpx.Response(200, json={
        "id": "MLB12345678", "title": "Samsung Galaxy", "price": 549, "currency_id": "BRL", "status": "active", "permalink": "https://produto.mercadolivre.com.br/MLB-12345678"}))
    res = await _server().call_tool("update_price", {"product_id": "MLB12345678", "price": 549})
    sc = res.structured_content
    assert res.is_error is False and sc["price"] == 549 and sc["currency"] == "BRL"
    req = route.calls.last.request
    assert json.loads(req.content) == {"price": 549} and req.headers["Authorization"] == "Bearer APP_USR-ml-access"


@pytest.mark.asyncio
@respx.mock
async def test_list_sales_searches_orders_of_the_configured_seller():
    _token()
    route = respx.get(url__startswith="https://api.mercadolibre.com/orders/search").mock(return_value=httpx.Response(200, json={"results": [
        {"id": 2000003508419013, "status": "paid", "date_created": "2013-05-27T10:01:50.000-04:00", "order_items": [{"item": {"id": "MLB12345678", "title": "Samsung Galaxy"}, "quantity": 1, "unit_price": 499}],
         "total_amount": 499, "currency_id": "BRL"}], "paging": {"total": 1, "offset": 0, "limit": 50}}))
    res = await _server().call_tool("list_sales", {"since": "2026-09-01T00:00:00.000-00:00"})
    s = res.structured_content["sales"][0]
    assert s["id"] == "2000003508419013" and s["product_id"] == "MLB12345678" and s["amount"] == 499 and res.structured_content["total"] == 1
    p = route.calls.last.request.url.params
    assert p["seller"] == "999" and p["sort"] == "date_desc" and p["order.date_created.from"] == "2026-09-01T00:00:00.000-00:00"


@pytest.mark.asyncio
@respx.mock
async def test_refused_refresh_is_an_auth_error_without_secrets():
    respx.post("https://api.mercadolibre.com/oauth/token").mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "message": "Error validating grant TG-ml-refresh-1"}))
    res = await _server().call_tool("get_product", {"product_id": "MLB1"})
    dumped = json.dumps(res.structured_content)
    assert res.structured_content["error"] == "auth_error" and "TG-ml-refresh-1" not in dumped and "ml-client-secret" not in dumped
