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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "etsy.json").read_text(encoding="utf-8"))
TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
BASE = "https://api.etsy.com/v3/application"
CREDS = {"client_id": "1aa2bb33c44d55eeeeee6fff", "api_key": "1aa2bb33c44d55eeeeee6fff:a1b2c3d4e5", "refresh_token": "12345678.REFRESHsecretVALUE", "shop_id": "5555",
         "taxonomy_id": "1633", "who_made": "i_did", "when_made": "made_to_order", "shipping_profile_id": "777", "readiness_state_id": "888"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], dict(CREDS), 50, "test")
    return build_server(SPEC, transport=t)


def _token_ok():
    return respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "12345678.ACCESS1", "token_type": "Bearer", "expires_in": 3600, "refresh_token": "12345678.NEXT"}))


@pytest.mark.asyncio
@respx.mock
async def test_refresh_grant_wire_shape_and_both_headers_on_the_api_call():
    token = _token_ok()
    me = respx.get(f"{BASE}/users/me").mock(return_value=httpx.Response(200, json={"user_id": 12345678, "shop_id": 5555}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["create_listing", "end_listing", "list_orders", "mark_shipped", "me", "update_listing"]  # set_inventory / listing_metrics not offered
    res = await server.call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["shop_id"] == 5555
    treq = token.calls.last.request
    assert parse_qs(treq.content.decode()) == {"grant_type": ["refresh_token"], "refresh_token": ["12345678.REFRESHsecretVALUE"], "client_id": ["1aa2bb33c44d55eeeeee6fff"]}
    assert "Authorization" not in treq.headers  # client_auth: body, no client secret in Etsy's refresh grant
    h = me.calls.last.request.headers
    assert h["Authorization"] == "Bearer 12345678.ACCESS1" and h["x-api-key"] == "1aa2bb33c44d55eeeeee6fff:a1b2c3d4e5"


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_maps_shop_receipts():
    _token_ok()
    route = respx.get(f"{BASE}/shops/5555/receipts").mock(return_value=httpx.Response(200, json={"count": 1, "results": [
        {"receipt_id": 1234567890, "status": "paid", "is_paid": True, "is_shipped": False, "created_timestamp": 1758700000,
         "grandtotal": {"amount": 2999, "divisor": 100, "currency_code": "USD"},
         "shipments": [{"receipt_shipping_id": 1, "carrier_name": "usps", "tracking_code": "9400111"}]}]}))
    res = await _server().call_tool("list_orders", {"since": "1758600000", "page": 2, "limit": 10})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["id"] == "1234567890" and o["status"] == "paid" and o["currency"] == "USD" and o["created_at"] == 1758700000 and o["tracking_number"] == "9400111"
    assert res.structured_content["total"] == 1 and res.structured_content["next_page"] is None
    p = route.calls.last.request.url.params
    assert p["limit"] == "10" and p["offset"] == "10" and p["min_created"] == "1758600000"


@pytest.mark.asyncio
@respx.mock
async def test_mark_shipped_posts_tracking_json_body():
    _token_ok()
    route = respx.post(f"{BASE}/shops/5555/receipts/1234567890/tracking").mock(return_value=httpx.Response(200, json={"receipt_id": 1234567890, "status": "completed", "is_shipped": True}))
    res = await _server().call_tool("mark_shipped", {"order_id": "1234567890", "carrier": "usps", "tracking_number": "9400111"})
    assert res.is_error is False and res.structured_content["status"] == "completed"
    assert json.loads(route.calls.last.request.content) == {"tracking_code": "9400111", "carrier_name": "usps"}


@pytest.mark.asyncio
@respx.mock
async def test_refused_refresh_token_is_an_auth_error_without_leaking_secrets_and_iso_since_is_invalid():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "error_description": "Invalid refresh token"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    text = json.dumps(res.structured_content)
    assert "REFRESHsecretVALUE" not in text and "a1b2c3d4e5" not in text
    _token_ok()
    res = await _server().call_tool("list_orders", {"since": "2026-09-01T00:00:00Z"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"  # min_created is an epoch integer


@pytest.mark.asyncio
@respx.mock
async def test_create_listing_posts_a_form_encoded_draft_listing():
    _token_ok()
    route = respx.post(f"{BASE}/shops/5555/listings").mock(return_value=httpx.Response(201, json={"listing_id": 1136716168, "state": "draft", "url": "https://www.etsy.com/listing/1136716168/yo-yo", "title": "Wooden yo-yo"}))
    res = await _server().call_tool("create_listing", {"title": "Wooden yo-yo", "description": "Hand turned", "price": 21.99, "quantity": 5, "sku": "YOYO-1"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["listing_id"] == "1136716168" and sc["status"] == "draft" and sc["url"].endswith("/yo-yo")
    req = route.calls.last.request
    assert req.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert parse_qs(req.content.decode()) == {"title": ["Wooden yo-yo"], "description": ["Hand turned"], "price": ["21.99"], "quantity": ["5"], "who_made": ["i_did"],
                                              "when_made": ["made_to_order"], "taxonomy_id": ["1633"], "type": ["physical"], "shipping_profile_id": ["777"], "readiness_state_id": ["888"]}
    assert req.headers["x-api-key"] == "1aa2bb33c44d55eeeeee6fff:a1b2c3d4e5"


@pytest.mark.asyncio
@respx.mock
async def test_update_and_end_listing_patch_form_bodies():
    _token_ok()
    route = respx.patch(f"{BASE}/shops/5555/listings/1136716168").mock(return_value=httpx.Response(200, json={"listing_id": 1136716168, "state": "inactive"}))
    res = await _server().call_tool("end_listing", {"listing_id": "1136716168"})
    assert res.is_error is False and res.structured_content["status"] == "inactive"
    assert route.calls.last.request.content.decode() == "state=inactive"
    assert route.calls.last.request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    res = await _server().call_tool("update_listing", {"listing_id": "1136716168", "title": "Maple yo-yo", "price": 30})
    assert res.is_error is False
    assert parse_qs(route.calls.last.request.content.decode()) == {"title": ["Maple yo-yo"]}  # price lives in the inventory offerings, not updateListing
