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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "bigbuy.json").read_text(encoding="utf-8"))


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds or {"api_key": "k"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_order", "get_order", "get_product", "list_products", "me", "track"]
    co = next(t for t in tools if t.name == "create_order")
    assert co.annotations.read_only_hint is False and co.annotations.destructive_hint is True
    assert co.input_schema["required"] == ["items", "shipping_address"]
    lp = next(t for t in tools if t.name == "list_products")
    assert lp.annotations.read_only_hint is True and lp.meta["platform_mcp/endpoint"] == "/rest/catalog/productsinformation.json"
    assert lp.meta["platform_mcp/docs"] == "https://api.bigbuy.eu/rest/doc"


@pytest.mark.asyncio
@respx.mock
async def test_list_products_uses_zero_based_pages_and_the_language_setting():
    # api.bigbuy.eu/rest/doc: GET /rest/catalog/productsinformation.{format} -> [ProductInformationDoc]
    respx.get("https://api.bigbuy.eu/rest/catalog/productsinformation.json").mock(return_value=httpx.Response(200, json=[
        {"id": 1234, "sku": "S12435678", "name": "Wire Scalp Massager", "description": "<p>...</p>", "url": "wire-scalp-massager", "isoCode": "en"}]))
    res = await _server({"api_key": "k", "iso_code": "en"}).call_tool("list_products", {"category": "11548", "page": 2, "limit": 50})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["products"][0] == {"id": "1234", "title": "Wire Scalp Massager", "sku": "S12435678", "url": "wire-scalp-massager", "description": "<p>...</p>",
                                 "raw": {"id": 1234, "sku": "S12435678", "name": "Wire Scalp Massager", "description": "<p>...</p>", "url": "wire-scalp-massager", "isoCode": "en"}}
    assert sc["total"] is None and sc["next_page"] is None  # one row < limit
    req = respx.calls.last.request
    assert req.url.params["page"] == "1" and req.url.params["pageSize"] == "50"
    assert req.url.params["parentTaxonomy"] == "11548" and req.url.params["isoCode"] == "en"
    assert req.headers["Authorization"] == "Bearer k"


@pytest.mark.asyncio
@respx.mock
async def test_create_order_wraps_the_body_in_order_and_reads_order_id():
    route = respx.post("https://api.bigbuy.eu/rest/order/create.json").mock(return_value=httpx.Response(201, json={"order_id": 123456}))
    res = await _server({"api_key": "k", "payment_method": "moneybox"}).call_tool("create_order", {
        "items": [{"reference": "S12435678", "quantity": 2}],
        "shipping_address": {"firstName": "Alejandro", "lastName": "Lopez", "country": "ES", "postcode": "46011", "town": "Valencia", "address": "Road 14", "phone": "789456123", "email": "a@example.com"},
        "shipping_option": "gls"})
    assert res.is_error is False
    assert res.structured_content["id"] == "123456"
    body = json.loads(route.calls.last.request.content)
    assert body == {"order": {"shippingAddress": {"firstName": "Alejandro", "lastName": "Lopez", "country": "ES", "postcode": "46011", "town": "Valencia", "address": "Road 14", "phone": "789456123", "email": "a@example.com"},
                              "products": [{"reference": "S12435678", "quantity": 2}], "paymentMethod": "moneybox"}}
    assert "carriers" not in body["order"] and "language" not in body["order"]  # unset settings are left out


@pytest.mark.asyncio
@respx.mock
async def test_track_returns_the_trackings_of_the_order_as_events():
    respx.get("https://api.bigbuy.eu/rest/tracking/order/123456.json").mock(return_value=httpx.Response(200, json=[
        {"id": 123456, "reference": "789456123", "trackings": [
            {"trackingNumber": "123456789", "statusDescription": "delivered", "statusDate": "2016-05-13 11:35:40", "carrier": {"id": "1234"}, "descriptionTranslated": None}]}]))
    res = await _server().call_tool("track", {"order_id": "123456"})
    assert res.is_error is False
    ev = res.structured_content["events"]
    assert len(ev) == 1 and ev[0]["tracking_number"] == "123456789" and ev[0]["status"] == "delivered" and ev[0]["carrier_id"] == "1234"


@pytest.mark.asyncio
@respx.mock
async def test_bad_key_is_an_auth_error_result():
    respx.get("https://api.bigbuy.eu/rest/user/auth/status.json").mock(return_value=httpx.Response(401, json={"code": 401, "message": "Invalid credentials"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
