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

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "etsy.json").read_text(encoding="utf-8"))
B = "https://api.etsy.com/v3/application"
CREDS = {"client_id": "keystr", "api_key": "keystr:etsy-shared-secret", "refresh_token": "123.etsy-refresh", "shop_id": "555",
         "taxonomy_id": "1", "who_made": "i_did", "when_made": "made_to_order", "shipping_profile_id": "77", "readiness_state_id": "88"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _token():
    return respx.post("https://api.etsy.com/v3/public/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "123.etsy-access", "expires_in": 3600, "refresh_token": "123.etsy-refresh-2"}))


@pytest.mark.asyncio
async def test_tools_follow_the_marketplaces_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_product", "get_product", "list_products", "list_sales", "me"]


@pytest.mark.asyncio
@respx.mock
async def test_list_products_filters_state_and_sends_both_auth_headers():
    _token()
    route = respx.get(url__startswith=f"{B}/shops/555/listings").mock(return_value=httpx.Response(200, json={"count": 1, "results": [
        {"listing_id": 1, "title": "Mug", "description": "d", "state": "active", "url": "https://www.etsy.com/listing/1", "price": {"amount": 1999, "divisor": 100, "currency_code": "USD"}, "created_timestamp": 1700000000}]}))
    res = await _server().call_tool("list_products", {"status": "active", "limit": 5})
    p = res.structured_content["products"][0]
    assert p["id"] == "1" and p["price"] == 1999 and p["currency"] == "USD" and p["status"] == "active"
    req = route.calls.last.request
    assert req.url.params["state"] == "active" and req.headers["x-api-key"] == "keystr:etsy-shared-secret" and req.headers["Authorization"] == "Bearer 123.etsy-access"


@pytest.mark.asyncio
@respx.mock
async def test_create_product_posts_a_draft_form_with_config_fields():
    _token()
    route = respx.post(f"{B}/shops/555/listings").mock(return_value=httpx.Response(201, json={"listing_id": 9, "title": "Mug", "state": "draft", "price": {"amount": 1999, "divisor": 100, "currency_code": "USD"}}))
    res = await _server().call_tool("create_product", {"name": "Mug", "description": "Blue", "price": 19.99, "currency": "USD"})
    assert res.is_error is False and res.structured_content["status"] == "draft"
    form = {k: v[0] for k, v in parse_qs(route.calls.last.request.content.decode()).items()}
    assert form == {"title": "Mug", "description": "Blue", "price": "19.99", "quantity": "1", "who_made": "i_did", "when_made": "made_to_order",
                    "taxonomy_id": "1", "type": "physical", "shipping_profile_id": "77", "readiness_state_id": "88"}


@pytest.mark.asyncio
@respx.mock
async def test_refused_refresh_is_an_auth_error_without_secrets():
    respx.post("https://api.etsy.com/v3/public/oauth/token").mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "error_description": "refresh token 123.etsy-refresh expired"}))
    res = await _server().call_tool("me", {})
    dumped = json.dumps(res.structured_content)
    assert res.structured_content["error"] == "auth_error" and "123.etsy-refresh" not in dumped and "etsy-shared-secret" not in dumped
