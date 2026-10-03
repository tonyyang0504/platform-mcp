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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "jumia.json").read_text(encoding="utf-8"))
API = "https://vendor-api.jumia.com"
CREDS = {"client_id": "jumia-self-app", "refresh_token": "RT1-refresh-secret"}


def _server(auth=None):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], auth or a["auth"], dict(CREDS), 50, "test"))


def _tok(access, refresh):
    return httpx.Response(200, json={"access_token": access, "token_type": "Bearer", "expires_in": 86399, "refresh_token": refresh, "refresh_expires_in": 2592000})


@pytest.mark.asyncio
@respx.mock
async def test_refresh_grant_in_body_without_secret():
    token = respx.post(f"{API}/token").mock(return_value=_tok("JWT1", "RT2-refresh-secret"))
    shops = respx.get(f"{API}/shops").mock(return_value=httpx.Response(200, json=[{"id": "b16a", "name": "Shop", "email": "s@x", "businessClients": []}]))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["list_orders", "me", "set_inventory"]
    assert (await server.call_tool("me", {})).is_error is False
    assert parse_qs(token.calls.last.request.content.decode()) == {"grant_type": ["refresh_token"], "refresh_token": ["RT1-refresh-secret"], "client_id": ["jumia-self-app"]}
    assert shops.calls.last.request.headers["Authorization"] == "Bearer JWT1"


@pytest.mark.asyncio
@respx.mock
async def test_rotated_refresh_token_is_persisted(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_MCP_STATE_DIR", str(tmp_path))
    respx.post(f"{API}/token").mock(return_value=_tok("JWT1", "RT2-refresh-secret"))
    respx.get(f"{API}/shops").mock(return_value=httpx.Response(200, json=[]))
    await _server({**SPEC["adapter"]["auth"], "state_key": "jumia"}).call_tool("me", {})
    assert json.loads((tmp_path / "jumia.json").read_text()) == {"refresh_token": "RT2-refresh-secret"}


@pytest.mark.asyncio
@respx.mock
async def test_stock_feed_and_orders():
    respx.post(f"{API}/token").mock(return_value=_tok("JWT1", "RT2-refresh-secret"))
    feed = respx.post(f"{API}/feeds/products/stock").mock(return_value=httpx.Response(201, json={"feedId": "07c390ae"}))
    res = await _server().call_tool("set_inventory", {"sku": "8682447314708", "listing_id": "07c390ae-d58a-42a2-8ec6-5051bca18cab", "quantity": 100})
    assert res.is_error is False and res.structured_content["status"] == "feed_created"
    assert json.loads(feed.calls.last.request.content) == {"products": [{"sellerSku": "8682447314708", "id": "07c390ae-d58a-42a2-8ec6-5051bca18cab", "stock": 100}]}
    orders = respx.get(f"{API}/orders").mock(return_value=httpx.Response(200, json={"orders": [
        {"id": "o-1", "number": "300000001", "status": "PENDING", "createdAt": "2026-09-20 10:00:00", "totalAmountLocal": {"currency": "NGN", "value": 15000}}]}))
    res = await _server().call_tool("list_orders", {"status": "PENDING", "since": "2026-09-01"})
    o = res.structured_content["orders"][0]
    assert o["id"] == "o-1" and o["total"] == 15000 and o["currency"] == "NGN"
    p = orders.calls.last.request.url.params
    assert p["status"] == "PENDING" and p["createdAfter"] == "2026-09-01"
