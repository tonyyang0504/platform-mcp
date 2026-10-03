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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "newegg.json").read_text(encoding="utf-8"))
API = "https://api.newegg.com/marketplace"
CREDS = {"api_key": "720ddc067f4d115bd544aff46bc75634", "secret_key": "21EC2020-3AEA-1069-A2DD-08002B30309D", "seller_id": "A006",
         "country_code": "USA", "currency": "USD", "warehouse_location": "USA"}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test")
    t.fixed_headers = a["headers"]
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
@respx.mock
async def test_me_sends_key_headers_and_seller_id():
    route = respx.get(f"{API}/sellermgmt/seller/accountstatus").mock(return_value=httpx.Response(200, json={"IsSuccess": True, "SellerID": "A006", "SellerName": "Acme", "Status": "Active"}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]
    assert (await server.call_tool("me", {})).is_error is False
    req = route.calls.last.request
    assert req.headers["Authorization"] == "720ddc067f4d115bd544aff46bc75634" and req.headers["SecretKey"] == "21EC2020-3AEA-1069-A2DD-08002B30309D"
    assert req.url.params["sellerid"] == "A006" and req.url.params["version"] == "307"


@pytest.mark.asyncio
@respx.mock
async def test_price_inventory_and_deactivate_bodies():
    price = respx.post(f"{API}/contentmgmt/item/international/price").mock(return_value=httpx.Response(200, json={"SellerID": "A006", "SellerPartNumber": "A006BSP3"}))
    await _server().call_tool("update_listing", {"listing_id": "A006BSP3", "price": 20.92})
    assert json.loads(price.calls.last.request.content) == {"Type": "1", "Value": "A006BSP3", "PriceList": {"Price": [{"CountryCode": "USA", "Currency": "USD", "SellingPrice": "20.92"}]}}
    res = await _server().call_tool("end_listing", {"listing_id": "A006BSP3"})
    assert res.structured_content["status"] == "deactivated"
    assert json.loads(price.calls.last.request.content)["PriceList"]["Price"][0]["Active"] == "0"
    inv = respx.post(f"{API}/contentmgmt/item/international/inventory").mock(return_value=httpx.Response(200, json={"SellerID": "A006"}))
    await _server().call_tool("set_inventory", {"sku": "A006BSP3", "quantity": 107})
    assert json.loads(inv.calls.last.request.content) == {"Type": "1", "Value": "A006BSP3", "InventoryList": {"Inventory": [{"WarehouseLocation": "USA", "AvailableQuantity": "107"}]}}


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_puts_order_info_request():
    route = respx.put(f"{API}/ordermgmt/order/orderinfo").mock(return_value=httpx.Response(200, json={"IsSuccess": True, "ResponseBody": {
        "PageInfo": {"TotalCount": 1, "TotalPageCount": 1, "PageIndex": 1, "PageSize": 100},
        "OrderInfoList": [{"OrderNumber": 511952652, "OrderStatus": 0, "OrderStatusDescription": "Unshipped", "OrderTotalAmount": 1.0, "CurrencyCode": "USD", "OrderDate": "03/18/2026 1:04:16"}]}}))
    res = await _server().call_tool("list_orders", {"status": "0", "since": "2026-09-01 00:00:00"})
    o = res.structured_content["orders"][0]
    assert o["id"] == "511952652" and o["status"] == "Unshipped" and o["total"] == 1.0 and res.structured_content["total"] == 1
    req = route.calls.last.request
    assert req.url.params["version"] == "304"
    assert json.loads(req.content) == {"OperationType": "GetOrderInfoRequest", "RequestBody": {"PageIndex": 1, "PageSize": 100, "RequestCriteria": {"Status": 0, "OrderDateFrom": "2026-09-01 00:00:00"}}}


@pytest.mark.asyncio
@respx.mock
async def test_error_array_is_upstream_error():
    respx.post(f"{API}/contentmgmt/item/international/price").mock(return_value=httpx.Response(400, json=[{"Code": "CT002", "Message": "Invalid SellerPartNumber"}]))
    res = await _server().call_tool("update_listing", {"listing_id": "nope", "price": 1})
    assert res.is_error is True and "CT002" in res.structured_content["message"]
