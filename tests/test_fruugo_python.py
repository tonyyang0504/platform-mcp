import base64
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "fruugo.json").read_text(encoding="utf-8"))
ORDERS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><o:orders merchantId="444" xmlns:o="https://www.fruugo.com/orders/schema">'
          '<o:order><o:customerOrderId>9135311</o:customerOrderId><o:orderId>9135311001000444</o:orderId><o:orderDate>2020-11-25T16:24:19.000+02:00</o:orderDate>'
          '<o:orderStatus>PENDING</o:orderStatus></o:order></o:orders>')


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"username": "shop@example.com", "password": "pw-secret-1"}, 50, "test"))


@pytest.mark.asyncio
async def test_tools():
    assert sorted(t.name for t in await _server().list_tools()) == ["end_listing", "list_orders", "mark_shipped", "me", "set_inventory"]


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_parses_namespaced_xml_with_basic_auth():
    route = respx.get(url__startswith="https://www.fruugo.com/orders/download/v2").mock(return_value=httpx.Response(200, headers={"content-type": "application/xml"}, text=ORDERS))
    res = await _server().call_tool("list_orders", {"since": "2020-11-25"})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["id"] == "9135311001000444" and o["status"] == "PENDING"
    req = route.calls[0].request
    assert req.url.params["from"] == "2020-11-25"
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(b"shop@example.com:pw-secret-1").decode()


@pytest.mark.asyncio
@respx.mock
async def test_set_inventory_posts_stock_xml_with_sku_attribute():
    route = respx.post("https://www.fruugo.com/stockstatus-api").mock(return_value=httpx.Response(200, headers={"content-type": "application/xml"}, text='<skus><sku fruugoSkuId="5146705"><itemsInStock>10</itemsInStock></sku></skus>'))
    res = await _server().call_tool("set_inventory", {"listing_id": "5146705", "quantity": 10})
    assert res.is_error is False and res.structured_content["status"] == "stock_updated"
    assert route.calls[0].request.content.decode() == '<?xml version="1.0" encoding="UTF-8"?><skus><sku fruugoSkuId="5146705"><itemsInStock>10</itemsInStock></sku></skus>'


@pytest.mark.asyncio
@respx.mock
async def test_end_listing_marks_not_available():
    route = respx.post("https://www.fruugo.com/stockstatus-api").mock(return_value=httpx.Response(200, text="<skus/>"))
    assert (await _server().call_tool("end_listing", {"listing_id": "5146706"})).is_error is False
    assert "<availability>NOTAVAILABLE</availability>" in route.calls[0].request.content.decode()


@pytest.mark.asyncio
@respx.mock
async def test_mark_shipped_form_post():
    route = respx.post("https://www.fruugo.com/orders/ship").mock(return_value=httpx.Response(200, text=ORDERS))
    res = await _server().call_tool("mark_shipped", {"order_id": "9135311001000444", "carrier": "Royal Mail", "tracking_number": "RM123"})
    assert res.is_error is False and res.structured_content["status"] == "shipped"
    assert parse_qs(route.calls[0].request.content.decode()) == {"orderId": ["9135311001000444"], "trackingCode": ["RM123"], "trackingUrl": ["Royal Mail"]}
