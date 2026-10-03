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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "gooten.json").read_text(encoding="utf-8"))
ORDERS = "https://api.print.io/api/v/5/source/api/orders/"


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], {"recipe_id": "RID", "partner_billing_key": "pbk-secret-9"}, 50, "test", envelope=a["envelope"])
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_order", "get_order", "list_products", "me", "track"]


@pytest.mark.asyncio
@respx.mock
async def test_create_order_sends_the_billing_key_in_the_payment_object():
    route = respx.post(ORDERS).mock(return_value=httpx.Response(200, json={"Id": "1-8b3c2d"}))
    addr = {"FirstName": "Jo", "LastName": "Doe", "Line1": "1 Main St", "City": "Austin", "State": "TX", "CountryCode": "US", "PostalCode": "73301", "Phone": "5551234", "Email": "jo@example.com"}
    res = await _server().call_tool("create_order", {"items": [{"SKU": "Mug-11oz", "Quantity": 1, "ShipType": "standard", "Images": [{"Url": "https://img.example/a.png"}]}], "shipping_address": addr})
    assert res.is_error is False and res.structured_content["id"] == "1-8b3c2d"
    req = route.calls.last.request
    assert req.url.params["recipeid"] == "RID"
    body = json.loads(req.content)
    assert body["Payment"] == {"PartnerBillingKey": "pbk-secret-9"} and body["ShipToAddress"]["PostalCode"] == "73301" and body["Items"][0]["SKU"] == "Mug-11oz"


@pytest.mark.asyncio
@respx.mock
async def test_get_order_and_track_read_the_items():
    respx.get(ORDERS).mock(return_value=httpx.Response(200, json={"Id": "1-8b3c2d", "NiceId": "123-456", "Items": [
        {"Sku": "Mug-11oz", "Quantity": 1, "Status": "Shipped", "TrackingNumber": "1Z999", "TrackingUrl": "https://ups/1Z999", "ShipCarrierName": "UPS"}]}))
    s = _server()
    res = await s.call_tool("get_order", {"id": "1-8b3c2d"})
    assert res.structured_content["status"] == "Shipped" and res.structured_content["tracking_number"] == "1Z999"
    tr = await s.call_tool("track", {"order_id": "1-8b3c2d"})
    assert tr.structured_content["events"][0]["carrier"] == "UPS"


@pytest.mark.asyncio
@respx.mock
async def test_had_error_is_a_tool_error_without_the_billing_key():
    respx.post(ORDERS).mock(return_value=httpx.Response(200, json={"HadError": True, "ErrorReferenceCode": "72f3", "Errors": [
        {"ErrorMessage": "'Postal Code' should not be empty.", "PropertyName": "Order.ShipToAddress.PostalCode", "AttemptedValue": "pbk-secret-9"}]}))
    res = await _server().call_tool("create_order", {"items": [{"SKU": "x", "Quantity": 1}], "shipping_address": {"FirstName": "Jo"}})
    assert res.is_error is True
    assert "pbk-secret-9" not in json.dumps(res.structured_content)
