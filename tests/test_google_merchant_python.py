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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "google_merchant.json").read_text(encoding="utf-8"))
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://merchantapi.googleapis.com"
CREDS = {"client_id": "cid.apps.googleusercontent.com", "client_secret": "GOCSPX-secret", "refresh_token": "1//refresh-secret",
         "account_id": "123456", "data_source": "accounts/123456/dataSources/104628", "content_language": "en", "feed_label": "US"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _token():
    return respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "ya29.token", "expires_in": 3599, "token_type": "Bearer"}))


@pytest.mark.asyncio
@respx.mock
async def test_refresh_in_body_and_account_probe():
    tok = _token()
    route = respx.get(f"{API}/accounts/v1/accounts/123456").mock(return_value=httpx.Response(200, json={"name": "accounts/123456", "accountName": "Shop"}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "me", "update_listing"]
    assert (await server.call_tool("me", {})).is_error is False
    form = parse_qs(tok.calls.last.request.content.decode())
    assert form["grant_type"] == ["refresh_token"] and form["client_id"] == ["cid.apps.googleusercontent.com"] and form["client_secret"] == ["GOCSPX-secret"]
    assert route.calls.last.request.headers["Authorization"] == "Bearer ya29.token"


@pytest.mark.asyncio
@respx.mock
async def test_patch_and_delete_product_input():
    _token()
    patch = respx.patch(f"{API}/products/v1/accounts/123456/productInputs/en~US~sku123").mock(return_value=httpx.Response(200, json={"name": "accounts/123456/productInputs/en~US~sku123"}))
    res = await _server().call_tool("update_listing", {"listing_id": "sku123", "title": "Blue mug", "price": 9.99})
    assert res.is_error is False and res.structured_content["status"] == "updated"
    req = patch.calls.last.request
    assert req.url.params["dataSource"] == "accounts/123456/dataSources/104628" and "updateMask" not in req.url.params
    assert json.loads(req.content) == {"productAttributes": {"title": "Blue mug"}}
    dele = respx.delete(f"{API}/products/v1/accounts/123456/productInputs/en~US~sku123").mock(return_value=httpx.Response(200, json={}))
    res = await _server().call_tool("end_listing", {"listing_id": "sku123"})
    assert res.is_error is False and res.structured_content["status"] == "deleted" and dele.called


@pytest.mark.asyncio
@respx.mock
async def test_revoked_refresh_token_is_auth_error_without_secrets():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "error_description": "Token 1//refresh-secret has been expired or revoked."}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    text = json.dumps(res.structured_content)
    assert "1//refresh-secret" not in text and "GOCSPX-secret" not in text
