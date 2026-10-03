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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "amazon.json").read_text(encoding="utf-8"))
TOKEN_URL = "https://api.amazon.com/auth/o2/token"
HOST = "https://sellingpartnerapi-eu.amazon.com"
CREDS = {"client_id": "amzn1.application-oa2-client.abc", "client_secret": "amzn1.oa2-cs.v1.SECRETvalue", "refresh_token": "Atzr|REFRESHsecretVALUE",
         "region": "eu", "seller_id": "A2SELLER", "marketplace_id": "A1F83G8C2ARO7P", "currency": "GBP"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], dict(CREDS), 50, "test")
    return build_server(SPEC, transport=t)


def _token_ok():
    return respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "Atza|ACCESS", "token_type": "bearer", "expires_in": 3600, "refresh_token": "Atzr|REFRESHsecretVALUE"}))


@pytest.mark.asyncio
@respx.mock
async def test_lwa_refresh_in_body_and_token_in_x_amz_access_token_without_bearer():
    token = _token_ok()
    me = respx.get(f"{HOST}/sellers/v1/marketplaceParticipations").mock(return_value=httpx.Response(200, json={"payload": [{"marketplace": {"id": "A1F83G8C2ARO7P", "countryCode": "GB"}, "participation": {"isParticipating": True}}]}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]
    res = await server.call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["payload"][0]["marketplace"]["countryCode"] == "GB"
    treq = token.calls.last.request
    assert parse_qs(treq.content.decode()) == {"grant_type": ["refresh_token"], "refresh_token": ["Atzr|REFRESHsecretVALUE"],
                                               "client_id": ["amzn1.application-oa2-client.abc"], "client_secret": ["amzn1.oa2-cs.v1.SECRETvalue"]}
    assert "Authorization" not in treq.headers
    h = me.calls.last.request.headers
    assert h["x-amz-access-token"] == "Atza|ACCESS" and "Authorization" not in h  # prefix "" and header redirect


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_maps_orders_v0():
    _token_ok()
    route = respx.get(f"{HOST}/orders/v0/orders").mock(return_value=httpx.Response(200, json={"payload": {"NextToken": "tok", "Orders": [
        {"AmazonOrderId": "202-1234567-1234567", "PurchaseDate": "2026-09-20T10:00:00Z", "LastUpdateDate": "2026-09-20T11:00:00Z", "OrderStatus": "Unshipped",
         "OrderTotal": {"CurrencyCode": "GBP", "Amount": "12.99"}}]}}))
    res = await _server().call_tool("list_orders", {"since": "2026-09-01T00:00:00Z", "status": "Unshipped", "limit": 20})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["id"] == "202-1234567-1234567" and o["status"] == "Unshipped" and o["total"] == "12.99" and o["currency"] == "GBP" and o["created_at"] == "2026-09-20T10:00:00Z"
    p = route.calls.last.request.url.params
    assert p["MarketplaceIds"] == "A1F83G8C2ARO7P" and p["CreatedAfter"] == "2026-09-01T00:00:00Z" and p["OrderStatuses"] == "Unshipped" and p["MaxResultsPerPage"] == "20"


@pytest.mark.asyncio
@respx.mock
async def test_set_inventory_and_update_listing_send_json_patch_merges():
    _token_ok()
    route = respx.patch(f"{HOST}/listings/2021-08-01/items/A2SELLER/SKU-1").mock(return_value=httpx.Response(200, json={"sku": "SKU-1", "status": "ACCEPTED", "submissionId": "f1", "issues": []}))
    res = await _server().call_tool("set_inventory", {"listing_id": "SKU-1", "quantity": 20})  # listing_id is the SKU on Amazon
    assert res.is_error is False and res.structured_content["status"] == "ACCEPTED"
    req = route.calls.last.request
    assert req.url.params["marketplaceIds"] == "A1F83G8C2ARO7P"
    assert json.loads(req.content) == {"productType": "PRODUCT", "patches": [{"op": "merge", "path": "/attributes/fulfillment_availability", "value": [{"fulfillment_channel_code": "DEFAULT", "quantity": 20}]}]}
    res = await _server().call_tool("update_listing", {"listing_id": "SKU-1", "price": 7.0})
    assert res.is_error is False
    assert json.loads(route.calls.last.request.content) == {"productType": "PRODUCT", "patches": [
        {"op": "merge", "path": "/attributes/purchasable_offer", "value": [{"marketplace_id": "A1F83G8C2ARO7P", "currency": "GBP", "audience": "ALL", "our_price": [{"schedule": [{"value_with_tax": 7.0}]}]}]},
        {"op": "merge", "path": "/attributes/fulfillment_availability", "value": [{"fulfillment_channel_code": "DEFAULT"}]}]}


@pytest.mark.asyncio
@respx.mock
async def test_denied_access_is_an_auth_error_without_secrets():
    _token_ok()
    respx.delete(f"{HOST}/listings/2021-08-01/items/A2SELLER/SKU-1").mock(return_value=httpx.Response(403, json={"errors": [{"code": "Unauthorized", "message": "Access to requested resource is denied.", "details": ""}]}))
    res = await _server().call_tool("end_listing", {"listing_id": "SKU-1"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 403
    text = json.dumps(res.structured_content)
    assert "REFRESHsecretVALUE" not in text and "SECRETvalue" not in text and "Atza|ACCESS" not in text
