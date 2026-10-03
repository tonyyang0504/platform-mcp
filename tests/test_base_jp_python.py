import json
import sys
from pathlib import Path
from urllib.parse import parse_qsl

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "base_jp.json").read_text(encoding="utf-8"))
CREDS = {"client_id": "cid-base-1", "client_secret": "SECRET-base-1", "refresh_token": "REFRESH-base-1", "redirect_uri": "https://app.example/base/callback"}
API = "https://api.thebase.in"


def _server(creds=None):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(creds or CREDS), 50, "test", envelope=a.get("envelope")))


def _token_route(new_refresh="REFRESH-base-2"):
    return respx.post(f"{API}/1/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "ACCESS-base", "token_type": "bearer", "expires_in": 3600, "refresh_token": new_refresh}))


@pytest.mark.asyncio
@respx.mock
async def test_refresh_sends_the_registered_redirect_uri():
    tok = _token_route()
    me = respx.get(f"{API}/1/users/me").mock(return_value=httpx.Response(200, json={"user": {"shop_id": "shop", "shop_name": "BASEショップ"}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["user"]["shop_id"] == "shop"
    form = dict(parse_qsl(tok.calls[0].request.content.decode()))
    assert form == {"grant_type": "refresh_token", "refresh_token": "REFRESH-base-1", "redirect_uri": "https://app.example/base/callback", "client_id": "cid-base-1", "client_secret": "SECRET-base-1"}
    assert me.calls[0].request.headers["Authorization"] == "Bearer ACCESS-base"


@pytest.mark.asyncio
@respx.mock
async def test_rotated_refresh_token_is_persisted(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_MCP_STATE_DIR", str(tmp_path))
    _token_route("REFRESH-base-rotated")
    respx.get(f"{API}/1/users/me").mock(return_value=httpx.Response(200, json={"user": {}}))
    assert (await _server().call_tool("me", {})).is_error is False
    assert json.loads((tmp_path / "base_jp.json").read_text())["refresh_token"] == "REFRESH-base-rotated"


@pytest.mark.asyncio
@respx.mock
async def test_list_and_get_products():
    _token_route()
    items = respx.get(url__startswith=f"{API}/1/items").mock(side_effect=lambda req: httpx.Response(200, json=(
        {"item": {"item_id": 1234, "title": "Tシャツ", "price": 3900, "stock": 10, "identifier": "TS-1", "img1_origin": "https://base-ec2.akamaized.net/x.jpg"}}
        if "/detail/" in req.url.path else {"items": [{"item_id": 1234, "title": "Tシャツ", "price": 3900, "stock": 10, "identifier": None}]})))
    s = _server()
    lst = await s.call_tool("list_products", {"limit": 10, "page": 3})
    assert lst.is_error is False and lst.structured_content["products"][0]["id"] == "1234" and lst.structured_content["products"][0]["currency"] == "JPY"
    assert dict(items.calls[0].request.url.params) == {"limit": "10", "offset": "20"}
    one = await s.call_tool("get_product", {"id": "1234"})
    assert one.is_error is False and one.structured_content["sku"] == "TS-1" and one.structured_content["price"] == 3900
    assert items.calls[1].request.url.path == "/1/items/detail/1234"


@pytest.mark.asyncio
@respx.mock
async def test_get_order_and_refused_refresh():
    _token_route()
    respx.get(f"{API}/1/orders/detail/154D88A39E454289").mock(return_value=httpx.Response(200, json={"order": {"unique_key": "154D88A39E454289", "ordered": 1396419762, "total": 8800, "dispatch_status": "dispatched", "tracking_number": "1234-1234-1234"}}))
    o = await _server().call_tool("get_order", {"id": "154D88A39E454289"})
    assert o.is_error is False and o.structured_content["status"] == "dispatched" and o.structured_content["tracking_number"] == "1234-1234-1234"
    respx.post(f"{API}/1/oauth/token").mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "error_description": "REFRESH-bad is invalid"}))
    bad = await _server({**CREDS, "refresh_token": "REFRESH-bad"}).call_tool("me", {})
    assert bad.is_error is True and bad.structured_content["error"] == "auth_error" and "REFRESH-bad" not in json.dumps(bad.structured_content)
