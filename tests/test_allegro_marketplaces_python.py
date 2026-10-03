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

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "allegro.json").read_text(encoding="utf-8"))
CREDS = {"client_id": "cid", "client_secret": "allegro-client-secret", "refresh_token": "allegro-refresh-1"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _token():
    return respx.post("https://allegro.pl/auth/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "allegro-access-1", "expires_in": 43199, "refresh_token": "allegro-refresh-2"}))


@pytest.mark.asyncio
async def test_tools_follow_the_marketplaces_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_product", "list_products", "list_refunds", "list_sales", "me", "update_price"]


@pytest.mark.asyncio
@respx.mock
async def test_list_products_maps_offers_with_vendor_media_type():
    _token()
    route = respx.get(url__startswith="https://api.allegro.pl/sale/offers").mock(return_value=httpx.Response(200, json={"offers": [
        {"id": "16885969603", "name": "Kubek", "sellingMode": {"price": {"amount": "49.99", "currency": "PLN"}}, "publication": {"status": "ACTIVE"}}], "count": 1, "totalCount": 1}))
    res = await _server().call_tool("list_products", {"status": "ACTIVE", "limit": 10})
    p = res.structured_content["products"][0]
    assert p["id"] == "16885969603" and p["price"] == "49.99" and p["currency"] == "PLN" and p["status"] == "ACTIVE"
    req = route.calls.last.request
    assert req.url.params["publication.status"] == "ACTIVE" and req.headers["Accept"] == "application/vnd.allegro.public.v1+json"
    assert req.headers["Authorization"] == "Bearer allegro-access-1"


@pytest.mark.asyncio
@respx.mock
async def test_update_price_patches_selling_mode_with_a_string_amount():
    _token()
    route = respx.patch("https://api.allegro.pl/sale/product-offers/123").mock(return_value=httpx.Response(200, json={"id": "123", "name": "Kubek", "sellingMode": {"price": {"amount": "59.90", "currency": "PLN"}}, "publication": {"status": "ACTIVE"}}))
    res = await _server().call_tool("update_price", {"product_id": "123", "price": 59.9, "currency": "PLN"})
    assert res.is_error is False and res.structured_content["price"] == "59.90"
    assert json.loads(route.calls.last.request.content) == {"sellingMode": {"price": {"amount": "59.9", "currency": "PLN"}}}


@pytest.mark.asyncio
@respx.mock
async def test_list_refunds_maps_refunds_and_token_errors_hide_secrets():
    _token()
    respx.get(url__startswith="https://api.allegro.pl/payments/refunds").mock(return_value=httpx.Response(200, json={"refunds": [
        {"id": "r-1", "payment": {"id": "p-1"}, "order": {"id": "o-1"}, "reason": "REFUND", "status": "SUCCESS", "createdAt": "2026-09-02T10:00:00Z", "totalValue": {"amount": "10.00", "currency": "PLN"}}], "count": 1, "totalCount": 1}))
    res = await _server().call_tool("list_refunds", {"since": "2026-09-01T00:00:00Z"})
    r = res.structured_content["refunds"][0]
    assert r["sale_id"] == "o-1" and r["amount"] == "10.00" and r["status"] == "SUCCESS"
    respx.post("https://allegro.pl/auth/oauth/token").mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "error_description": "Invalid refresh token: allegro-refresh-1"}))
    res = await _server().call_tool("me", {})
    dumped = json.dumps(res.structured_content)
    assert res.structured_content["error"] == "auth_error" and "allegro-refresh-1" not in dumped and "allegro-client-secret" not in dumped
