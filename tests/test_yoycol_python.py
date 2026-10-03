import base64
import hashlib
import hmac
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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "yoycol.json").read_text(encoding="utf-8"))
CREDS = {"access_key": "AK-yoy-1", "secret_key": "yoy-secret-0123456789"}
BASE = "https://www.yoycol.com/api/2025/open/v4"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _expected(req, params):
    h = req.headers
    data = (f"method={req.method}\npath={req.url.path}\ntimestamp={h['X-API-Timestamp']}\nnonce={h['X-API-Nonce']}\naccessKey=AK-yoy-1\n"
            f"algorithm=HmacSHA256\nversion=4.0\nparams=" + "&".join(f"{k}={params[k]}" for k in sorted(params)))
    return base64.b64encode(hmac.new(b"yoy-secret-0123456789", data.encode(), hashlib.sha256).digest()).decode()


@pytest.mark.asyncio
@respx.mock
async def test_list_products_is_signed_with_the_v4_signature_data():
    route = respx.get(f"{BASE}/catalog/products").mock(return_value=httpx.Response(200, json={"code": "100000", "msg": "success", "data": {"total": 3, "pages": 1, "records": [
        {"id": 101, "spuCode": "TS-001", "name": "Unisex T-Shirt", "spuDisplayImg": "https://img.yoycol.com/1.jpg", "onlineStatus": True}]}}))
    res = await _server().call_tool("list_products", {"query": "shirt tee", "limit": 10})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "101" and p["title"] == "Unisex T-Shirt" and p["sku"] == "TS-001"
    req = route.calls.last.request
    h = req.headers
    assert h["X-API-Access-Key"] == "AK-yoy-1" and h["X-API-Algorithm"] == "HmacSHA256" and h["X-API-Version"] == "4.0"
    assert len(h["X-API-Nonce"]) == 32 and h["X-API-Timestamp"].isdigit()
    assert h["X-API-Signature"] == _expected(req, {"page": "1", "query": "shirt tee", "size": "10"})


@pytest.mark.asyncio
@respx.mock
async def test_get_product_and_sku_quotes():
    pr = respx.get(f"{BASE}/catalog/products/101").mock(return_value=httpx.Response(200, json={"code": "100000", "data": {"product": {"id": 101, "name": "Unisex T-Shirt", "spuCode": "TS-001"},
        "variants": [{"id": 9, "skuCode": "TS-001-BLK-M", "salesPrice": 6.5, "currency": "USD"}]}}))
    respx.get(f"{BASE}/shipping/sku_quotes").mock(return_value=httpx.Response(200, json={"code": "100000", "data": [
        {"regionCode": "US", "regionName": "United States", "primaryRegion": True, "levels": [{"levelCode": "STD", "firstPrice": 4.99, "additionalPrice": 2.0}]}]}))
    s = _server()
    g = await s.call_tool("get_product", {"id": "101"})
    assert g.structured_content["sku"] == "TS-001-BLK-M" and g.structured_content["price"] == 6.5
    req = pr.calls.last.request
    assert req.url.params["include"] == "variants" and req.headers["X-API-Signature"] == _expected(req, {"include": "variants"})
    q = await s.call_tool("quote_shipping", {"product_id": "TS-001-BLK-M", "country": "US"})
    assert q.structured_content["options"][0]["region"] == "US"


@pytest.mark.asyncio
@respx.mock
async def test_business_error_code_is_an_error_and_writes_are_not_offered():
    respx.get(f"{BASE}/catalog/products").mock(return_value=httpx.Response(200, json={"code": "300003", "msg": "OPENAPI_V4_AUTH_ERROR_SIGNATURE_INVALID", "data": None}))
    s = _server()
    res = await s.call_tool("me", {})
    assert res.is_error is True
    assert "yoy-secret-0123456789" not in json.dumps(res.structured_content)
    names = sorted(t.name for t in await s.list_tools())
    assert names == ["get_product", "list_products", "me", "quote_shipping"]
