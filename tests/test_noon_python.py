import json
import sys
from pathlib import Path

import httpx
import jwt as pyjwt
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "noon.json").read_text(encoding="utf-8"))
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PEM = KEY.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
CREDS = {"key_id": "KEY-noon-1", "private_key": PEM, "project_code": "PRJ123", "warehouse_code": "WH-DXB-1", "country_code": "ae"}
BASE = "https://noon-api-gateway.noon.partners"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _login():
    return respx.post(BASE + "/identity/public/v1/api/login").mock(return_value=httpx.Response(200, json={}, headers=[
        ("set-cookie", "_npsid=SESS-noon-1; Path=/; HttpOnly; Secure"), ("set-cookie", "_nprt=REFRESH-noon-1; Path=/; HttpOnly")]))


@pytest.mark.asyncio
@respx.mock
async def test_rs256_login_jwt_and_every_cookie_replayed():
    login = _login()
    who = respx.get(BASE + "/identity/v1/whoami").mock(return_value=httpx.Response(200, json={"user_code": "U1", "username": "svc@shop"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["username"] == "svc@shop"
    body = json.loads(login.calls[0].request.content)
    assert body["default_project_code"] == "PRJ123"
    claims = pyjwt.decode(body["token"], KEY.public_key(), algorithms=["RS256"])
    assert claims["sub"] == "KEY-noon-1" and isinstance(claims["iat"], int) and claims["jti"]
    h = who.calls[0].request.headers
    assert h["Cookie"] == "_npsid=SESS-noon-1; _nprt=REFRESH-noon-1" and "Authorization" not in h


@pytest.mark.asyncio
@respx.mock
async def test_stock_and_price_updates():
    _login()
    stock = respx.post(BASE + "/stock/v1/stock-update").mock(return_value=httpx.Response(200, json={"items": [{"warehouse_code": "WH-DXB-1", "partner_sku": "SKU-9", "status": {"status_code": "OK", "message": ""}}]}))
    price = respx.post(BASE + "/pricing/v1/pricing/upsert").mock(return_value=httpx.Response(200, json={"items": [{"partner_sku": "SKU-9", "country_code": "ae", "status": {"status_code": "OK"}}]}))
    s = _server()
    r = await s.call_tool("set_inventory", {"sku": "SKU-9", "quantity": 7})
    assert r.structured_content["status"] == "submitted" and r.structured_content["result_code"] == "OK"
    assert json.loads(stock.calls[0].request.content) == {"items": [{"warehouse_code": "WH-DXB-1", "partner_sku": "SKU-9", "qty": 7}]}
    u = await s.call_tool("update_listing", {"listing_id": "SKU-9", "price": 129.5})
    assert u.is_error is False
    assert json.loads(price.calls[0].request.content) == {"items": [{"partner_sku": "SKU-9", "country_code": "ae", "price": 129.5}]}
    e = await s.call_tool("end_listing", {"listing_id": "SKU-9"})
    assert e.is_error is False and json.loads(price.calls[1].request.content)["items"][0]["is_active"] is False


@pytest.mark.asyncio
@respx.mock
async def test_fbpi_orders_with_next_token():
    _login()
    route = respx.post(url__startswith=BASE + "/fbpi/v1/fbpi-orders/list").mock(side_effect=[
        httpx.Response(200, json={"next_token": "NT-2", "orders": [{"fbpi_order_nr": "F1", "mp_order_nr": "N123", "mp_code": "noon", "currency_code": "AED", "items": [], "order_created_at": "2026-09-20T10:00:00Z"}]}),
        httpx.Response(200, json={"next_token": "", "orders": []})])
    s = _server()
    r = await s.call_tool("list_orders", {"since": "2026-09-01"})
    assert r.structured_content["orders"][0]["id"] == "F1" and r.structured_content["next_cursor"] == "NT-2"
    first = route.calls[0].request
    assert "next_token" not in first.url.params
    assert json.loads(first.content) == {"warehouse_code": "WH-DXB-1", "created_after": "2026-09-01T00:00:00Z"}
    r2 = await s.call_tool("list_orders", {"since": "2026-09-01", "cursor": "NT-2"})
    assert route.calls[1].request.url.params["next_token"] == "NT-2" and r2.structured_content["next_cursor"] is None


@pytest.mark.asyncio
@respx.mock
async def test_login_without_cookies_is_an_auth_error():
    respx.post(BASE + "/identity/public/v1/api/login").mock(return_value=httpx.Response(200, json={}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
