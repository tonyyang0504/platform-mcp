import base64
import json
import os
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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "allegro.json").read_text(encoding="utf-8"))
TOKEN_URL = "https://allegro.pl/auth/oauth/token"
API = "https://api.allegro.pl"
VND = "application/vnd.allegro.public.v1+json"
CREDS = {"client_id": "cid-123", "client_secret": "SECRETvalue", "refresh_token": "R1-REFRESHsecret", "currency": "PLN"}


def _server(auth=None):
    t = Transport(SPEC["adapter"]["base_url"], auth or SPEC["adapter"]["auth"], dict(CREDS), 50, "test")
    return build_server(SPEC, transport=t)


def _tok(access, refresh):
    return httpx.Response(200, json={"access_token": access, "token_type": "bearer", "refresh_token": refresh, "expires_in": 43199, "scope": "allegro_api", "jti": "x"})


@pytest.mark.asyncio
@respx.mock
async def test_basic_client_auth_refresh_and_vendor_media_type_headers():
    token = respx.post(TOKEN_URL).mock(return_value=_tok("A1", "R2-REFRESHsecret"))
    me = respx.get(f"{API}/me").mock(return_value=httpx.Response(200, json={"id": "43120000", "login": "seller", "baseMarketplace": {"id": "allegro-pl"}}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "mark_shipped", "me", "set_inventory", "update_listing"]
    res = await server.call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["login"] == "seller"
    treq = token.calls.last.request
    assert treq.headers["Authorization"] == "Basic " + base64.b64encode(b"cid-123:SECRETvalue").decode()
    assert parse_qs(treq.content.decode()) == {"grant_type": ["refresh_token"], "refresh_token": ["R1-REFRESHsecret"]}
    h = me.calls.last.request.headers
    assert h["Authorization"] == "Bearer A1" and h["Accept"] == VND


@pytest.mark.asyncio
@respx.mock
async def test_single_use_refresh_token_rotates_and_is_persisted(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_MCP_STATE_DIR", str(tmp_path))
    token = respx.post(TOKEN_URL).mock(side_effect=[_tok("A1", "R2-REFRESHsecret"), _tok("A2", "R3-REFRESHsecret"), _tok("A3", "R4-REFRESHsecret")])
    respx.get(f"{API}/me").mock(side_effect=[httpx.Response(200, json={"id": "1"}), httpx.Response(401, json={"error": "invalid_token"}), httpx.Response(200, json={"id": "1"})])
    server = _server({**SPEC["adapter"]["auth"], "state_key": "allegro"})
    assert (await server.call_tool("me", {})).is_error is False
    assert (await server.call_tool("me", {})).is_error is False  # 401 -> re-mint with the ROTATED token
    sent = [parse_qs(c.request.content.decode())["refresh_token"][0] for c in token.calls]
    assert sent == ["R1-REFRESHsecret", "R2-REFRESHsecret"]
    state = tmp_path / "allegro.json"
    assert json.loads(state.read_text()) == {"refresh_token": "R3-REFRESHsecret"} and (os.stat(state).st_mode & 0o777) == 0o600
    # a restarted server prefers the saved token over the (already used) environment value
    fresh = _server({**SPEC["adapter"]["auth"], "state_key": "allegro"})
    respx.get(f"{API}/me").mock(return_value=httpx.Response(200, json={"id": "1"}))
    assert (await fresh.call_tool("me", {})).is_error is False
    assert parse_qs(token.calls.last.request.content.decode())["refresh_token"] == ["R3-REFRESHsecret"]


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_maps_checkout_forms():
    respx.post(TOKEN_URL).mock(return_value=_tok("A1", "R2-REFRESHsecret"))
    route = respx.get(f"{API}/order/checkout-forms").mock(return_value=httpx.Response(200, json={"count": 1, "totalCount": 7, "checkoutForms": [
        {"id": "29b0bc59-0a1c-11ef-9d4b-4d0b4f3f8a4e", "status": "READY_FOR_PROCESSING", "fulfillment": {"status": "NEW"},
         "summary": {"totalToPay": {"amount": "123.45", "currency": "PLN"}}, "lineItems": [{"id": "li-1", "boughtAt": "2026-09-20T10:00:00.000Z"}]}]}))
    res = await _server().call_tool("list_orders", {"status": "NEW", "since": "2026-09-01T00:00:00Z", "limit": 1})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["id"] == "29b0bc59-0a1c-11ef-9d4b-4d0b4f3f8a4e" and o["status"] == "NEW" and o["total"] == "123.45" and o["currency"] == "PLN" and o["created_at"] == "2026-09-20T10:00:00.000Z"
    assert res.structured_content["total"] == 7 and res.structured_content["next_page"] == 2
    p = route.calls.last.request.url.params
    assert p["fulfillment.status"] == "NEW" and p["lineItems.boughtAt.gte"] == "2026-09-01T00:00:00Z" and p["limit"] == "1" and p["offset"] == "0"


@pytest.mark.asyncio
@respx.mock
async def test_writes_keep_the_vendor_content_type_and_build_the_documented_bodies():
    respx.post(TOKEN_URL).mock(return_value=_tok("A1", "R2-REFRESHsecret"))
    patch = respx.patch(f"{API}/sale/product-offers/7766554433").mock(return_value=httpx.Response(200, json={"id": "7766554433", "publication": {"status": "ACTIVE"}}))
    res = await _server().call_tool("update_listing", {"listing_id": "7766554433", "price": 220.85, "quantity": 10})
    assert res.is_error is False and res.structured_content["status"] == "accepted"
    req = patch.calls.last.request
    assert req.headers["Content-Type"] == VND
    assert json.loads(req.content) == {"sellingMode": {"price": {"amount": "220.85", "currency": "PLN"}}, "stock": {"available": 10}}
    end = respx.put(url__regex=rf"{API}/sale/offer-publication-commands/[0-9a-f-]{{36}}").mock(return_value=httpx.Response(201, json={"id": "c1", "taskCount": {"total": 1}}))
    res = await _server().call_tool("end_listing", {"listing_id": "7766554433"})
    assert res.is_error is False and res.structured_content["status"] == "end_requested"
    assert json.loads(end.calls.last.request.content) == {"offerCriteria": [{"offers": [{"id": "7766554433"}], "type": "CONTAINS_OFFERS"}], "publication": {"action": "END"}}
    ship = respx.post(f"{API}/order/checkout-forms/o-1/shipments").mock(return_value=httpx.Response(201, json={"id": "s1", "waybill": "6200000000"}))
    res = await _server().call_tool("mark_shipped", {"order_id": "o-1", "carrier": "INPOST", "tracking_number": "6200000000"})
    assert res.is_error is False and json.loads(ship.calls.last.request.content) == {"carrierId": "INPOST", "waybill": "6200000000"}


@pytest.mark.asyncio
@respx.mock
async def test_used_refresh_token_is_an_auth_error_without_secrets():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "error_description": "Invalid refresh token: R1-REFRESHsecret"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    text = json.dumps(res.structured_content)
    assert "R1-REFRESHsecret" not in text and "SECRETvalue" not in text
