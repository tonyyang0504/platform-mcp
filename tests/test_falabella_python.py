import hashlib
import hmac
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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "falabella.json").read_text(encoding="utf-8"))
BASE = "https://sellercenter-api.falabella.com/"
OK = '<?xml version="1.0" encoding="UTF-8"?><SuccessResponse><Head><RequestId>f8bf8d09-1647</RequestId><RequestAction>ProductUpdate</RequestAction><ResponseType/><Timestamp>2015-07-02T12:19:49+0200</Timestamp></Head><Body/></SuccessResponse>'
ORDERS = ('<?xml version="1.0" encoding="UTF-8"?><SuccessResponse><Head><RequestId/><RequestAction>GetOrders</RequestAction><TotalCount>2</TotalCount></Head><Body><Orders>'
          '<Order><OrderId>1104089001</OrderId><CreatedAt>2025-04-03 12:00:00</CreatedAt><Statuses><Status>ready_to_ship</Status></Statuses></Order>'
          '<Order><OrderId>1104089002</OrderId><CreatedAt>2025-04-03 12:05:00</CreatedAt><Statuses><Status>pending</Status></Statuses></Order></Orders></Body></SuccessResponse>')


def _server():
    a = SPEC["adapter"]
    creds = {"api_key": "fal-key-123", "user_id": "seller@example.com", "operator_code": "facl"}
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], creds, 50, "test", envelope=a["envelope"]))


def _check_sig(req):
    query = req.url.query.decode()
    signed, _, sig = query.rpartition("&Signature=")
    names = [p.split("=", 1)[0] for p in signed.split("&")]
    assert names == sorted(names)
    assert sig == hmac.new(b"fal-key-123", signed.encode(), hashlib.sha256).hexdigest()
    assert req.url.params["UserID"] == "seller@example.com" and req.url.params["Version"] == "1.0"


@pytest.mark.asyncio
async def test_tools():
    assert sorted(t.name for t in await _server().list_tools()) == ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_signs_sorted_query_and_parses_xml():
    route = respx.get(url__startswith=BASE).mock(return_value=httpx.Response(200, headers={"content-type": "text/xml"}, text=ORDERS))
    res = await _server().call_tool("list_orders", {"since": "2025-04-01T00:00:00+00:00", "status": "ready_to_ship", "limit": 2})
    sc = res.structured_content
    assert res.is_error is False and [o["id"] for o in sc["orders"]] == ["1104089001", "1104089002"]
    assert sc["total"] == 2 and sc["next_page"] is None  # the XML TotalCount (a string) is read: 2 of 2 shown, no next page
    req = route.calls[0].request
    assert req.url.params["Action"] == "GetOrders" and req.url.params["CreatedAfter"] == "2025-04-01T00:00:00+00:00"
    assert req.url.params["Limit"] == "2" and req.url.params["Offset"] == "0"
    assert "CreatedAfter=2025-04-01T00%3A00%3A00%2B00%3A00" in req.url.query.decode()
    _check_sig(req)


@pytest.mark.asyncio
@respx.mock
async def test_update_listing_posts_xml_product_update():
    route = respx.post(url__startswith=BASE).mock(return_value=httpx.Response(200, headers={"content-type": "text/xml"}, text=OK))
    res = await _server().call_tool("update_listing", {"listing_id": "SKU-1", "price": 59990, "quantity": 40})
    assert res.is_error is False and res.structured_content["status"] == "feed_queued" and res.structured_content["feed_id"] == "f8bf8d09-1647"
    req = route.calls[0].request
    assert req.url.params["Action"] == "ProductUpdate" and req.headers["Content-Type"] == "application/xml"
    assert req.content.decode() == ('<?xml version="1.0" encoding="UTF-8"?><Request><Product><SellerSku>SKU-1</SellerSku><BusinessUnits><BusinessUnit>'
                                    '<OperatorCode>facl</OperatorCode><Price>59990</Price><Stock>40</Stock></BusinessUnit></BusinessUnits></Product></Request>')
    _check_sig(req)


@pytest.mark.asyncio
@respx.mock
async def test_set_inventory_update_stock_body():
    route = respx.post(url__startswith=BASE).mock(return_value=httpx.Response(200, text=OK))
    res = await _server().call_tool("set_inventory", {"sku": "abc02", "quantity": 234})
    assert res.is_error is False
    assert route.calls[0].request.url.params["Action"] == "UpdateStock"
    assert "<Warehouse><Stock><SellerSku>abc02</SellerSku><Quantity>234</Quantity></Stock></Warehouse>" in route.calls[0].request.content.decode()


@pytest.mark.asyncio
@respx.mock
async def test_error_response_is_an_error():
    respx.post(url__startswith=BASE).mock(return_value=httpx.Response(200, text='<?xml version="1.0"?><ErrorResponse><Head><RequestAction>ProductRemove</RequestAction><ErrorType>Sender</ErrorType><ErrorCode>1000</ErrorCode><ErrorMessage>Format Error Detected</ErrorMessage></Head><Body/></ErrorResponse>'))
    res = await _server().call_tool("end_listing", {"listing_id": "SKU-1"})
    assert res.is_error is True
