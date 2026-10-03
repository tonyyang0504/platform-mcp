import json
import re
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "ingram_micro.json").read_text(encoding="utf-8"))
CREDS = {"client_id": "im-client", "client_secret": "im-secret-0123456789", "customer_number": "20-222222", "country_code": "US", "customer_contact": "buyer@reseller.test"}
BASE = "https://api.ingrammicro.com:443"
TOKEN = "https://api.ingrammicro.com:443/oauth/oauth30/token"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_catalog_search_carries_token_account_headers_and_a_fresh_correlation_id():
    tok = respx.post(TOKEN).mock(return_value=httpx.Response(200, json={"access_token": "im-access-token-xyz", "expires_in": 86399}))
    route = respx.get(f"{BASE}/resellers/v6/catalog").mock(return_value=httpx.Response(200, json={"recordsFound": 1180, "pageSize": 25, "pageNumber": 1, "catalog": [
        {"ingramPartNumber": "1A8249", "vendorPartNumber": "SDSQUNC-016G-AN6IA", "description": "CLASS 10 100MB/S UHS-I CARD", "vendorName": "Sandisk Mobile", "upcCode": "0619659134587"}]}))
    s = _server()
    res = await s.call_tool("list_products", {"query": "sandisk"})
    await s.call_tool("list_products", {"query": "sandisk"})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "1A8249" and p["sku"] == "SDSQUNC-016G-AN6IA" and res.structured_content["total"] == 1180
    body = dict(x.split("=") for x in tok.calls.last.request.content.decode().split("&"))
    assert body["grant_type"] == "client_credentials" and body["client_id"] == "im-client"
    r1, r2 = route.calls[0].request, route.calls[1].request
    assert r1.headers["Authorization"] == "Bearer im-access-token-xyz"
    assert r1.headers["IM-CustomerNumber"] == "20-222222" and r1.headers["IM-CountryCode"] == "US"
    assert re.fullmatch(r"[0-9a-f]{32}", r1.headers["IM-CorrelationID"]) and r1.headers["IM-CorrelationID"] != r2.headers["IM-CorrelationID"]
    assert r1.url.params["keyword"] == "sandisk" and r1.url.params["pageSize"] == "25"
    assert "sign" not in r1.url.params


@pytest.mark.asyncio
@respx.mock
async def test_create_order_body_shape():
    respx.post(TOKEN).mock(return_value=httpx.Response(200, json={"access_token": "im-access-token-xyz", "expires_in": 86399}))
    route = respx.post(f"{BASE}/resellers/v6/orders").mock(return_value=httpx.Response(201, json={"customerOrderNumber": "MCP260925101010", "purchaseOrderTotal": 14.29,
        "orders": [{"ingramOrderNumber": "20-RFKW4", "ingramOrderDate": "2026-09-25", "currencyCode": "USD", "lines": [{"lineStatus": "Backordered"}]}]}))
    items = [{"customerLineNumber": "1", "ingramPartNumber": "DF4128", "quantity": 1}]
    addr = {"contact": "TOM SORENSEN", "addressLine1": "17501 W 98TH ST", "city": "LENEXA", "state": "KS", "postalCode": "662191736", "countryCode": "US"}
    res = await _server().call_tool("create_order", {"items": items, "shipping_address": addr, "shipping_option": "RG"})
    assert res.is_error is False and res.structured_content["id"] == "20-RFKW4" and res.structured_content["total"] == 14.29
    sent = json.loads(route.calls.last.request.content)
    assert sent["lines"] == items and sent["shipToInfo"] == addr and sent["shipmentDetails"] == {"carrierCode": "RG"}
    assert re.fullmatch(r"MCP\d{12}", sent["customerOrderNumber"])


@pytest.mark.asyncio
@respx.mock
async def test_freight_estimate_and_order_tracking():
    respx.post(TOKEN).mock(return_value=httpx.Response(200, json={"access_token": "im-access-token-xyz", "expires_in": 86399}))
    fr = respx.post(f"{BASE}/resellers/v6/freightestimate").mock(return_value=httpx.Response(200, json={"freightEstimateResponse": {"currencyCode": "USD", "distribution": [
        {"shipFromBranchNumber": "10", "carrierCode": "RG", "shipVia": "FEDEX GROUND", "freightRate": 19.7, "transitDays": 1}]}}))
    respx.get(f"{BASE}/resellers/v6.1/orders/20-RD3QV").mock(return_value=httpx.Response(200, json={"ingramOrderNumber": "20-RD3QV", "orderStatus": "Shipped", "orderTotal": 25371.27, "currencyCode": "USD",
        "lines": [{"lineStatus": "Shipped", "ingramPartNumber": "4AW708", "shipmentDetails": [{"carrierDetails": [{"carrierName": "FEDEX", "shippedDate": "2026-09-20", "trackingDetails": [{"trackingNumber": "390064340282"}]}]}]}]}))
    s = _server()
    q = await s.call_tool("quote_shipping", {"product_id": "A300-123", "country": "US", "quantity": 2})
    assert q.structured_content["options"][0]["name"] == "FEDEX GROUND" and q.structured_content["options"][0]["price"] == 19.7
    req = fr.calls.last.request
    assert json.loads(req.content) == {"shipToAddress": {"countryCode": "US"}, "lines": [{"customerLineNumber": "001", "ingramPartNumber": "A300-123", "quantity": "2"}]}
    assert req.headers["IM-CustomerContact"] == "buyer@reseller.test"
    o = await s.call_tool("get_order", {"id": "20-RD3QV"})
    assert o.structured_content["status"] == "Shipped" and o.structured_content["tracking_number"] == "390064340282"
    t = await s.call_tool("track", {"order_id": "20-RD3QV"})
    assert t.structured_content["events"][0]["carrier"] == "FEDEX"


@pytest.mark.asyncio
@respx.mock
async def test_refused_token_is_an_auth_error_without_the_secret():
    respx.post(TOKEN).mock(return_value=httpx.Response(401, text="invalid_client im-secret-0123456789"))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "im-secret-0123456789" not in json.dumps(res.structured_content)
