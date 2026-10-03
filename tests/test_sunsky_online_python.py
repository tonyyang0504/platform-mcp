import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "sunsky_online.json").read_text(encoding="utf-8"))
CREDS = {"key": "MYKEY", "secret": "MYSECRET-sunsky-01", "language": "en"}
BASE = "https://open.sunsky-online.com/openapi/"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _check_sign(request):
    params = dict(parse_qsl(urlsplit(str(request.url)).query, keep_blank_values=True))
    sig = params.pop("signature")
    # MD5(values sorted by their parameter names, key included, + '@' + secret)
    assert sig == hashlib.md5(("".join(params[k] for k in sorted(params)) + "@" + CREDS["secret"]).encode()).hexdigest()
    assert params["key"] == "MYKEY" and CREDS["secret"] not in str(request.url)
    return params


@pytest.mark.asyncio
@respx.mock
async def test_search_is_signed_over_sorted_values():
    route = respx.post(BASE + "product!search.do").mock(return_value=httpx.Response(200, json={"result": "success", "data": {"total": 81, "pageCount": 3, "result": [
        {"id": 3889036, "itemNo": "EDA008394601A", "name": "LED badge", "price": "2.79", "stock": 120, "groupItemNo": "EDA0083946", "categoryId": 123, "status": 1}]}}))
    res = await _server().call_tool("list_products", {"category": "123", "page": 2, "limit": 40})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "EDA008394601A" and p["price"] == "2.79" and p["stock"] == 120
    assert res.structured_content["total"] == 81
    q = _check_sign(route.calls.last.request)
    assert q == {"key": "MYKEY", "categoryId": "123", "page": "2", "pageSize": "40", "lang": "en"}


@pytest.mark.asyncio
@respx.mock
async def test_documented_signature_example():
    # the convention's own example: name=John Smith, age=19, gendar=mail, key=MYKEY → MD5("19mailMYKEYJohn Smith@MYSECRET")
    spec = json.loads(json.dumps(SPEC))
    spec["adapter"]["tools"]["me"]["fixed_params"] = {"name": "John Smith", "age": "19", "gendar": "mail"}
    route = respx.post(url__startswith=BASE + "order!getBalance.do").mock(return_value=httpx.Response(200, json={"result": "success", "data": "5.2600"}))
    a = spec["adapter"]
    server = build_server(spec, transport=Transport(a["base_url"], a["auth"], {"key": "MYKEY", "secret": "MYSECRET"}, 50, "test", envelope=a["envelope"]))
    res = await server.call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["data"] == "5.2600"
    q = dict(parse_qsl(urlsplit(str(route.calls.last.request.url)).query))
    assert q["signature"] == hashlib.md5(b"19mailMYKEYJohn Smith@MYSECRET").hexdigest()


@pytest.mark.asyncio
@respx.mock
async def test_create_order_flattens_items_and_address():
    route = respx.post(BASE + "order!createOrder.do").mock(return_value=httpx.Response(200, json={"result": "success", "data": {
        "number": "2301144841", "status": 1, "totalAmount": "18.3300", "gmtCreated": "2026-9-25 05:55:50", "trackingNumber": None}}))
    items = [{"itemNo": "TBD06062381", "qty": 2}, {"itemNo": "EDA008394601A", "qty": 1, "remark": "gift"}]
    addr = {"countryId": 41, "state": "TX", "city": "Austin", "address": "1 Main St", "postcode": "78701", "receiver": "Ann Lee", "shipment": "drop", "siteNumber": "BAC-112"}
    res = await _server().call_tool("create_order", {"items": items, "shipping_address": addr, "shipping_option": "278"})
    assert res.is_error is False
    assert res.structured_content["id"] == "2301144841" and res.structured_content["total"] == "18.3300"
    q = _check_sign(route.calls.last.request)
    assert q["items.1.itemNo"] == "TBD06062381" and q["items.1.qty"] == "2" and q["items.2.remark"] == "gift" and "items.3.itemNo" not in q
    assert q["deliveryAddress.countryId"] == "41" and q["deliveryAddress.receiver"] == "Ann Lee" and q["deliveryAddress.shippingWayId"] == "278"
    assert q["deliveryAddress.shipment"] == "drop" and q["siteNumber"] == "BAC-112"


@pytest.mark.asyncio
@respx.mock
async def test_quote_shipping_and_track():
    respx.post(BASE + "order!getPricesAndFreights.do").mock(return_value=httpx.Response(200, json={"result": "success", "data": {
        "freightList": [{"id": 278, "name": "USPS Agent(YanWen Express)", "shippingCost": "10.70", "transitTime": "8 - 12"}], "priceList": []}}))
    respx.post(BASE + "order!getOrderDetails.do").mock(return_value=httpx.Response(200, json={"result": "success", "data": {
        "number": "2301144841", "status": 5, "trackingNumber": "YT23098888", "shippingWay": {"name": "Postnord", "queryUrl": "https://t.17track.net/en#nums="}}}))
    s = _server()
    q = await s.call_tool("quote_shipping", {"product_id": "EDA008394601A", "country": "41", "quantity": 10})
    assert q.structured_content["options"][0]["id"] == "278" and q.structured_content["options"][0]["cost"] == "10.70"
    req = dict(parse_qsl(urlsplit(str(respx.calls[0].request.url)).query))
    assert req["countryId"] == "41" and req["items.1.itemNo"] == "EDA008394601A" and req["items.1.qty"] == "10"
    t = await s.call_tool("track", {"order_id": "2301144841"})
    assert t.structured_content["tracking_number"] == "YT23098888" and t.structured_content["carrier"] == "Postnord"


@pytest.mark.asyncio
@respx.mock
async def test_error_result_is_an_is_error():
    respx.post(BASE + "product!detail.do").mock(return_value=httpx.Response(200, json={"result": "error", "messages": ["NO_PERMISSION_DUE_TO_SIGNATURE"]}))
    res = await _server().call_tool("get_product", {"id": "X"})
    assert res.is_error is True and "NO_PERMISSION_DUE_TO_SIGNATURE" in json.dumps(res.structured_content)
    assert CREDS["secret"] not in json.dumps(res.structured_content)
