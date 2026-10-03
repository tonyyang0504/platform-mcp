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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "pinterest_catalogs.json").read_text(encoding="utf-8"))
API = "https://api.pinterest.com/v5"
CREDS = {"client_id": "1484", "client_secret": "PINSECRETvalue", "refresh_token": "pinr.refresh1", "country": "US", "language": "en-US", "currency": "USD"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _token():
    return respx.post(f"{API}/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "pina.access", "expires_in": 2592000, "refresh_token": "pinr.refresh2", "token_type": "bearer"}))


@pytest.mark.asyncio
@respx.mock
async def test_basic_refresh_and_user_account():
    tok = _token()
    respx.get(f"{API}/user_account").mock(return_value=httpx.Response(200, json={"username": "shop", "account_type": "BUSINESS"}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "me", "update_listing"]
    assert (await server.call_tool("me", {})).structured_content["account"]["username"] == "shop"
    req = tok.calls.last.request
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(b"1484:PINSECRETvalue").decode()
    assert parse_qs(req.content.decode())["refresh_token"] == ["pinr.refresh1"]


@pytest.mark.asyncio
@respx.mock
async def test_items_batch_update_and_delete():
    _token()
    route = respx.post(f"{API}/catalogs/items/batch").mock(return_value=httpx.Response(200, json={"batch_id": "b1", "catalog_type": "RETAIL", "created_time": "2026-09-25T10:00:00", "status": "PROCESSING"}))
    res = await _server().call_tool("update_listing", {"listing_id": "DS0294-M", "price": 24.99, "title": "Denim shirt"})
    assert res.structured_content["status"] == "PROCESSING"
    assert json.loads(route.calls.last.request.content) == {"catalog_type": "RETAIL", "country": "US", "language": "en-US",
        "items": [{"item_id": "DS0294-M", "operation": "UPDATE", "attributes": {"title": "Denim shirt", "price": "24.99 USD"}}]}
    await _server().call_tool("end_listing", {"listing_id": "DS0294-M"})
    assert json.loads(route.calls.last.request.content)["items"] == [{"item_id": "DS0294-M", "operation": "DELETE"}]


@pytest.mark.asyncio
@respx.mock
async def test_error_body_is_invalid_input():
    _token()
    respx.post(f"{API}/catalogs/items/batch").mock(return_value=httpx.Response(400, json={"code": 1, "message": "Invalid parameters."}))
    res = await _server().call_tool("end_listing", {"listing_id": "X"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"
