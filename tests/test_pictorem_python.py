import json
import sys
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "pictorem.json").read_text(encoding="utf-8"))
CREDS = {"artflow_key": "AFK-test-0123456789"}
BASE = "https://www.pictorem.com/artflow/0.1"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _form(request):
    assert request.headers["content-type"].startswith("multipart/form-data; boundary=")
    msg = BytesParser(policy=default).parsebytes(b"Content-Type: " + request.headers["content-type"].encode() + b"\r\n\r\n" + request.content)
    return {p.get_param("name", header="content-disposition"): p.get_content() for p in msg.iter_parts()}


@pytest.mark.asyncio
@respx.mock
async def test_send_order_is_multipart_with_the_artflow_key():
    route = respx.post(BASE + "/sendorder/").mock(return_value=httpx.Response(200, json={"status": True, "msg": [], "orderid": 472175}))
    items = [{"code": "1|canvas|stretched|horizontal|16|12", "fileurl": "https://img.example.com/a.jpg", "filetype": "jpg", "bordercolorhex": "ffffff"},
             {"code": "1|acrylic|da8|horizontal|16|12", "collectionID": 357936}]
    addr = {"firstname": "Kathleen", "lastname": "Bernal", "address1": "3371 Sycamore Lake Road", "city": "Oshkosh", "province": "WI", "country": "USA", "cp": "54901", "po": "MY-PO-1"}
    res = await _server().call_tool("create_order", {"items": items, "shipping_address": addr})
    assert res.is_error is False and res.structured_content["id"] == "472175"
    req = route.calls[0].request
    assert req.headers["ArtFlowKey"] == CREDS["artflow_key"]
    form = _form(req)
    assert form["orderList[0][code]"] == "1|canvas|stretched|horizontal|16|12" and form["orderList[0][fileurl]"] == "https://img.example.com/a.jpg"
    assert form["orderList[1][collectionID]"] == "357936" and "orderList[1][fileurl]" not in form and "orderList[2][code]" not in form
    assert form["deliveryInfo[cp]"] == "54901" and form["deliveryInfo[country]"] == "USA" and form["po"] == "MY-PO-1"


@pytest.mark.asyncio
@respx.mock
async def test_order_status_and_tracking():
    route = respx.post(BASE + "/getorderstatus/").mock(return_value=httpx.Response(200, json={"status": True, "msg": [], "order": {
        "orderid": 472174, "po": "MY-PO-1", "date": "2026-03-15 10:22:00", "order_status_label": "Shipped", "production_status_label": "Shipped", "production_progress": 100,
        "tracking_number": "1Z999AA10123456784", "tracking_carrier": "UPS", "total": 125.4, "currency": "USD", "lines": []}}))
    s = _server()
    o = await s.call_tool("get_order", {"id": "472174"})
    assert o.structured_content["status"] == "Shipped" and o.structured_content["total"] == 125.4
    assert _form(route.calls[0].request) == {"orderid": "472174"}
    t = await s.call_tool("track", {"order_id": "472174"})
    assert t.structured_content["tracking_number"] == "1Z999AA10123456784" and t.structured_content["carrier"] == "UPS"


@pytest.mark.asyncio
@respx.mock
async def test_artworks_and_probe():
    respx.post(BASE + "/getartworklist/").mock(return_value=httpx.Response(200, json={"status": True, "data": {"total": 147, "artworks": [{"id": 2452666, "name": "Mona Lisa", "url": "https://www.pictorem.com/2452666/Mona-Lisa.html", "image": {"thumb": "https://x/t.jpg"}}]}}))
    me = respx.post(BASE + "/getorderlist/").mock(return_value=httpx.Response(200, json={"status": True, "data": {"total": 63, "orders": []}}))
    s = _server()
    a = await s.call_tool("list_products", {"limit": 24})
    assert a.structured_content["products"][0]["title"] == "Mona Lisa" and a.structured_content["total"] == 147
    assert (await s.call_tool("me", {})).is_error is False
    assert _form(me.calls[0].request) == {"page": "1", "limit": "1"}


@pytest.mark.asyncio
@respx.mock
async def test_status_false_is_an_error():
    respx.post(BASE + "/getorderstatus/").mock(return_value=httpx.Response(200, json={"status": False, "msg": {"error": ["Order not found."]}}))
    res = await _server().call_tool("get_order", {"id": "1"})
    assert res.is_error is True and "Order not found." in json.dumps(res.structured_content)
