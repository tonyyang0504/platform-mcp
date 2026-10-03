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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "ebay.json").read_text(encoding="utf-8"))
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
CREDS = {"client_id": "MyApp-PRD-1234", "client_secret": "PRD-CERTsecretVALUE", "refresh_token": "v^1.1#i^1#REFRESHsecretVALUE", "currency": "USD"}
SCOPES = "https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.account"


def _server(creds=CREDS):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], dict(creds), 50, "test")
    return build_server(SPEC, transport=t)


def _token_ok():
    return respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "v^1.1#i^1#ACCESS", "expires_in": 7200, "token_type": "User Access Token"}))


@pytest.mark.asyncio
@respx.mock
async def test_refresh_grant_uses_basic_client_auth_and_scope_then_bearer():
    token = _token_ok()
    me = respx.get("https://api.ebay.com/sell/account/v1/privilege").mock(return_value=httpx.Response(200, json={"sellerRegistrationCompleted": True, "sellingLimit": {"quantity": 100}}))
    server = _server()
    names = sorted(t.name for t in await server.list_tools())
    assert names == ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]  # create_listing / mark_shipped / listing_metrics not offered
    res = await server.call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["sellerRegistrationCompleted"] is True
    treq = token.calls.last.request
    assert treq.headers["Authorization"] == "Basic " + base64.b64encode(b"MyApp-PRD-1234:PRD-CERTsecretVALUE").decode()
    assert parse_qs(treq.content.decode()) == {"grant_type": ["refresh_token"], "refresh_token": ["v^1.1#i^1#REFRESHsecretVALUE"], "scope": [SCOPES]}
    assert me.calls.last.request.headers["Authorization"] == "Bearer v^1.1#i^1#ACCESS"


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_maps_fulfillment_orders():
    _token_ok()
    route = respx.get("https://api.ebay.com/sell/fulfillment/v1/order").mock(return_value=httpx.Response(200, json={"href": "x", "total": 3, "limit": 2, "offset": 0, "orders": [
        {"orderId": "05-12345-67890", "orderFulfillmentStatus": "NOT_STARTED", "creationDate": "2026-09-20T10:00:00.000Z", "pricingSummary": {"total": {"value": "25.98", "currency": "USD"}}},
        {"orderId": "05-12345-67891", "orderFulfillmentStatus": "FULFILLED", "creationDate": "2026-09-19T10:00:00.000Z", "pricingSummary": {"total": {"value": "9.99", "currency": "USD"}}}]}))
    res = await _server().call_tool("list_orders", {"limit": 2})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["id"] == "05-12345-67890" and o["status"] == "NOT_STARTED" and o["total"] == "25.98" and o["currency"] == "USD" and o["created_at"] == "2026-09-20T10:00:00.000Z"
    assert res.structured_content["total"] == 3 and res.structured_content["next_page"] == 2
    p = route.calls.last.request.url.params
    assert p["limit"] == "2" and p["offset"] == "0"


@pytest.mark.asyncio
@respx.mock
async def test_update_listing_and_set_inventory_build_bulk_price_quantity_bodies():
    _token_ok()
    route = respx.post("https://api.ebay.com/sell/inventory/v1/bulk_update_price_quantity").mock(return_value=httpx.Response(200, json={"responses": [{"statusCode": 200, "sku": "SKU-1", "offerId": "123456"}]}))
    res = await _server().call_tool("update_listing", {"listing_id": "123456", "price": 19.5, "quantity": 4})
    assert res.is_error is False and res.structured_content["status"] == "submitted" and res.structured_content["raw"]["statusCode"] == 200
    assert json.loads(route.calls.last.request.content) == {"requests": [{"offers": [{"offerId": "123456", "availableQuantity": 4, "price": {"value": "19.5", "currency": "USD"}}]}]}
    res = await _server().call_tool("set_inventory", {"sku": "SKU-1", "quantity": 7})
    assert res.is_error is False
    assert json.loads(route.calls.last.request.content) == {"requests": [{"sku": "SKU-1", "shipToLocationAvailability": {"quantity": 7}}]}


@pytest.mark.asyncio
@respx.mock
async def test_end_listing_withdraws_and_a_revoked_token_is_an_auth_error_without_secrets():
    _token_ok()
    route = respx.post("https://api.ebay.com/sell/inventory/v1/offer/123456/withdraw").mock(return_value=httpx.Response(200, json={"listingId": "110552236789"}))
    res = await _server().call_tool("end_listing", {"listing_id": "123456"})
    assert res.is_error is False and res.structured_content["status"] == "withdrawn" and route.calls.last.request.content in (b"", None)
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "error_description": "the provided authorization refresh token is invalid or was issued to another client"}))
    res = await _server().call_tool("list_orders", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    text = json.dumps(res.structured_content)
    assert "REFRESHsecretVALUE" not in text and "CERTsecretVALUE" not in text
