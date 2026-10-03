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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "bonanza.json").read_text(encoding="utf-8"))
URL = "https://api.bonanza.com/api_requests/secure_request"
CREDS = {"dev_id": "DEVID-123456", "cert_id": "CERTID-abcdef", "auth_token": "USERTOKEN-secret99"}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a["envelope"])
    t.fixed_headers = a.get("headers") or {}
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
@respx.mock
async def test_me_sends_dev_cert_headers_and_token_in_body():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"ack": "Success", "getTokenStatusResponse": {"verified": True, "hardExpirationTime": "2027-09-01T00:00:00Z"}}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["create_listing", "end_listing", "list_orders", "mark_shipped", "me"]
    res = await server.call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["getTokenStatusResponse"]["verified"] is True
    req = route.calls.last.request
    assert req.headers["X-BONANZLE-API-DEV-NAME"] == "DEVID-123456" and req.headers["X-BONANZLE-API-CERT-NAME"] == "CERTID-abcdef"
    assert json.loads(req.content) == {"getTokenStatusRequest": {"requesterCredentials": {"bonanzleAuthToken": "USERTOKEN-secret99"}}}


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_reads_order_array_wrappers():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"ack": "Success", "getOrdersResponse": {
        "orderArray": [{"order": {"orderID": 1811, "orderStatus": "Completed", "total": "104.32", "createdTime": "2026-09-20T16:54:25Z"}}],
        "hasMoreOrders": "false", "paginationResult": {"totalNumberOfEntries": 1, "totalNumberOfPages": 1}, "pageNumber": 1}}))
    res = await _server().call_tool("list_orders", {"status": "Completed", "since": "2026-09-01T00:00:00Z", "limit": 50})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["id"] == "1811" and o["status"] == "Completed" and o["total"] == "104.32" and res.structured_content["total"] == 1
    body = json.loads(route.calls.last.request.content)["getOrdersRequest"]
    assert body["orderRole"] == "seller" and body["orderStatus"] == "Completed" and body["createTimeFrom"] == "2026-09-01T00:00:00Z"
    assert body["paginationInput"] == {"entriesPerPage": 50, "pageNumber": 1}


@pytest.mark.asyncio
@respx.mock
async def test_create_listing_and_mark_shipped_bodies():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"ack": "Success", "addFixedPriceItemResponse": {"itemId": 205172, "categoryId": 163128, "sellingState": "Active"}}))
    res = await _server().call_tool("create_listing", {"title": "Lightsaber", "price": 42, "quantity": 3, "sku": "LS-1", "image_urls": ["https://img.example/a.png"]})
    assert res.is_error is False and res.structured_content["listing_id"] == "205172" and res.structured_content["status"] == "Active"
    item = json.loads(route.calls.last.request.content)["addFixedPriceItemRequest"]["item"]
    assert item == {"title": "Lightsaber", "price": 42, "quantity": 3, "sku": "LS-1", "pictureDetails": {"pictureURL": ["https://img.example/a.png"]}, "allowForSale": True}
    route.mock(return_value=httpx.Response(200, json={"ack": "Success", "completeSaleResponse": {"skippedProcessing": False}}))
    res = await _server().call_tool("mark_shipped", {"order_id": "1811", "carrier": "usps", "tracking_number": "9400100000000000000000"})
    assert res.is_error is False and res.structured_content["status"] == "shipped"
    body = json.loads(route.calls.last.request.content)["completeSaleRequest"]
    assert body["transactionID"] == 1811 and body["shipped"] is True and body["shipment"] == {"shippingTrackingNumber": "9400100000000000000000", "shippingCarrierUsed": "usps"}


@pytest.mark.asyncio
@respx.mock
async def test_failure_ack_is_an_error_without_the_token():
    respx.post(URL).mock(return_value=httpx.Response(200, json={"ack": "Failure", "errorMessage": {"error": [{"type": "InvalidAuthToken", "message": "bad token USERTOKEN-secret99"}]}}))
    res = await _server().call_tool("end_listing", {"listing_id": "205172"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "USERTOKEN-secret99" not in json.dumps(res.structured_content)
