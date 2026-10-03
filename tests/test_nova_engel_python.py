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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "nova_engel.json").read_text(encoding="utf-8"))
CREDS = {"user": "shop-user", "password": "PASSWORD-nova-1", "language": "es"}
BASE = "https://drop.novaengel.com"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _login(token="TOKEN-ne-1"):
    return respx.post(BASE + "/api/login").mock(return_value=httpx.Response(200, json={"Token": token}))


@pytest.mark.asyncio
@respx.mock
async def test_login_then_token_in_the_product_paging_path():
    login = _login()
    route = respx.get(BASE + "/api/products/paging/TOKEN-ne-1/2/20/es").mock(return_value=httpx.Response(200, json=[
        {"Id": 1234, "EANs": ["8411061000000"], "Description": "Eau de toilette 100 ml", "Price": 21.5, "PVR": 45.0, "Stock": 12, "BrandName": "Acme", "Families": ["Perfumes"]}]))
    res = await _server().call_tool("list_products", {"page": 2, "limit": 20})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "1234" and p["price"] == 21.5 and p["stock"] == 12 and p["ean"] == "8411061000000"
    assert json.loads(login.calls[0].request.content) == {"User": "shop-user", "Password": "PASSWORD-nova-1"}
    assert "Authorization" not in route.calls[0].request.headers


@pytest.mark.asyncio
@respx.mock
async def test_probe_reuses_the_session_token():
    login = _login()
    probe = respx.get(BASE + "/api/products/paging/TOKEN-ne-1/1/1/es").mock(return_value=httpx.Response(200, json=[{"Id": 1}]))
    s = _server()
    assert (await s.call_tool("me", {})).is_error is False
    assert (await s.call_tool("me", {})).is_error is False
    assert login.call_count == 1 and probe.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_send_order_v2_array_body():
    _login()
    route = respx.post(BASE + "/api/orders/sendv2/TOKEN-ne-1").mock(return_value=httpx.Response(200, json=[{"BookingCode": "BK-9", "Errors": [], "Message": "OK", "OrderNumber": "PO-77"}]))
    res = await _server().call_tool("create_order", {
        "items": [{"product_id": "1234", "quantity": 2}, {"product_id": 99, "quantity": 1}],
        "shipping_address": {"order_number": "PO-77", "name": "Ana", "second_name": "Pérez", "street": "Calle Mayor 1", "city": "Madrid", "county": "Madrid", "postal_code": "28013", "country": "ES", "telephone": "600000000"}})
    assert res.is_error is False and res.structured_content["id"] == "PO-77" and res.structured_content["booking_code"] == "BK-9"
    body = json.loads(route.calls[0].request.content)
    assert isinstance(body, list) and len(body) == 1
    assert body[0]["Lines"] == [{"ProductId": 1234, "Units": 2}, {"ProductId": 99, "Units": 1}]
    assert body[0]["OrderNumber"] == "PO-77" and body[0]["PostalCode"] == "28013" and body[0]["SecondName"] == "Pérez"


@pytest.mark.asyncio
@respx.mock
async def test_order_and_tracking():
    _login()
    respx.get(BASE + "/api/orders/orderbyid/TOKEN-ne-1/PO-77").mock(return_value=httpx.Response(200, json={
        "OrderNumber": "PO-77", "Invoice": "F-1", "Date": "2026-09-20T10:00:00", "Total": 55.3, "Status": 4,
        "SendInfo": {"Tracking": "1Z999", "Carrier": "GLS", "Expedition": "E-1", "TrackingURL": "https://gls.example/1Z999"}, "Lines": []}))
    s = _server()
    o = await s.call_tool("get_order", {"id": "PO-77"})
    assert o.structured_content["id"] == "PO-77" and o.structured_content["total"] == 55.3 and o.structured_content["tracking_number"] == "1Z999"
    assert o.structured_content["status"] == "4"  # auth audit: vocabulary status is a string
    t = await s.call_tool("track", {"order_id": "PO-77"})
    ev = t.structured_content["events"]  # auth audit: the vocabulary requires an events array
    assert ev[0]["carrier"] == "GLS" and ev[0]["tracking_url"] == "https://gls.example/1Z999" and ev[0]["tracking_number"] == "1Z999"
