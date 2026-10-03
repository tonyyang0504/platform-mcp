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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "mercado_libre.json").read_text(encoding="utf-8"))
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
API = "https://api.mercadolibre.com"
CREDS = {"client_id": "1234567890", "client_secret": "SECRETvalue", "refresh_token": "TG-REFRESHsecret-1", "seller_id": "1108966308"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], dict(CREDS), 50, "test")
    return build_server(SPEC, transport=t)


def _tok(access, refresh):
    return httpx.Response(200, json={"access_token": access, "token_type": "Bearer", "expires_in": 21600, "scope": "offline_access read write", "user_id": 1108966308, "refresh_token": refresh})


@pytest.mark.asyncio
@respx.mock
async def test_body_client_auth_refresh_and_in_memory_rotation():
    token = respx.post(TOKEN_URL).mock(side_effect=[_tok("APP_USR-A1", "TG-REFRESHsecret-2"), _tok("APP_USR-A2", "TG-REFRESHsecret-3")])
    me = respx.get(f"{API}/users/me").mock(side_effect=[httpx.Response(200, json={"id": 1108966308, "nickname": "SELLER"}), httpx.Response(401, json={"message": "invalid access token"}), httpx.Response(200, json={"id": 1108966308})])
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "me", "set_inventory", "update_listing"]
    assert (await server.call_tool("me", {})).is_error is False
    first = parse_qs(token.calls[0].request.content.decode())
    assert first == {"grant_type": ["refresh_token"], "refresh_token": ["TG-REFRESHsecret-1"], "client_id": ["1234567890"], "client_secret": ["SECRETvalue"]}
    assert "Authorization" not in token.calls[0].request.headers and me.calls[0].request.headers["Authorization"] == "Bearer APP_USR-A1"
    assert (await server.call_tool("me", {})).is_error is False
    assert parse_qs(token.calls[1].request.content.decode())["refresh_token"] == ["TG-REFRESHsecret-2"]  # the single-use token was rotated


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_maps_order_search():
    respx.post(TOKEN_URL).mock(return_value=_tok("APP_USR-A1", "TG-REFRESHsecret-2"))
    route = respx.get(f"{API}/orders/search").mock(return_value=httpx.Response(200, json={"results": [
        {"id": 2000003508419013, "status": "paid", "date_created": "2026-09-20T10:30:00.000-03:00", "total_amount": 880.0, "currency_id": "MXN", "shipping": {"id": 41000000001}}],
        "paging": {"total": 1, "offset": 0, "limit": 50}}))
    res = await _server().call_tool("list_orders", {"status": "paid", "since": "2026-09-01T00:00:00.000-00:00"})
    assert res.is_error is False
    o = res.structured_content["orders"][0]
    assert o["id"] == "2000003508419013" and o["status"] == "paid" and o["total"] == 880.0 and o["currency"] == "MXN"
    assert res.structured_content["total"] == 1
    p = route.calls.last.request.url.params
    assert p["seller"] == "1108966308" and p["order.status"] == "paid" and p["order.date_created.from"] == "2026-09-01T00:00:00.000-00:00" and p["sort"] == "date_desc" and p["limit"] == "50"


@pytest.mark.asyncio
@respx.mock
async def test_item_updates_are_json_puts():
    respx.post(TOKEN_URL).mock(return_value=_tok("APP_USR-A1", "TG-REFRESHsecret-2"))
    route = respx.put(f"{API}/items/MLA1136716168").mock(return_value=httpx.Response(200, json={"id": "MLA1136716168", "status": "active", "available_quantity": 6}))
    res = await _server().call_tool("update_listing", {"listing_id": "MLA1136716168", "title": "Zapatillas", "price": 15000, "quantity": 6})
    assert res.is_error is False and res.structured_content["status"] == "active"
    assert json.loads(route.calls.last.request.content) == {"title": "Zapatillas", "price": 15000, "available_quantity": 6}
    await _server().call_tool("end_listing", {"listing_id": "MLA1136716168"})
    assert json.loads(route.calls.last.request.content) == {"status": "paused"}
    await _server().call_tool("set_inventory", {"listing_id": "MLA1136716168", "quantity": 0})
    assert json.loads(route.calls.last.request.content) == {"available_quantity": 0}


@pytest.mark.asyncio
@respx.mock
async def test_used_refresh_token_is_an_auth_error_without_secrets():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "error_description": "Error validating grant. Your authorization code or refresh token may be expired or it was already used", "refresh_token": "TG-REFRESHsecret-1"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    text = json.dumps(res.structured_content)
    assert "TG-REFRESHsecret-1" not in text and "SECRETvalue" not in text
