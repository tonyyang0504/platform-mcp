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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "kaufland_marketplace.json").read_text(encoding="utf-8"))
BASE = "https://sellerapi.kaufland.com/v2"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_key": "CK32", "secret_key": "kf-secret-64", "storefront": "de"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_are_seller_side_reads():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_order", "get_product", "list_products", "me"]


@pytest.mark.asyncio
@respx.mock
async def test_search_is_signed_over_the_full_uri():
    route = respx.get(f"{BASE}/products/search").mock(return_value=httpx.Response(200, json={
        "data": [{"id_product": 123456, "title": "Kaffeemaschine", "url": "https://www.kaufland.de/product/123456/", "main_picture": "https://media.cdn.kaufland.de/x.jpg", "eans": ["4006381333931"]}],
        "pagination": {"offset": 0, "limit": 20, "total": 41}}))
    res = await _server().call_tool("list_products", {"query": "kaffee"})
    sc = res.structured_content
    assert sc["products"][0]["id"] == "123456" and sc["total"] == 41
    req = route.calls.last.request
    assert req.headers["Shop-Client-Key"] == "CK32"
    ts = req.headers["Shop-Timestamp"]
    uri = str(req.url)
    assert "q=kaffee" in uri and "storefront=de" in uri
    expected = hmac.new(b"kf-secret-64", f"GET\n{uri}\n\n{ts}".encode(), hashlib.sha256).hexdigest()
    assert req.headers["Shop-Signature"] == expected


@pytest.mark.asyncio
@respx.mock
async def test_get_order_maps_the_first_order_unit():
    respx.get(f"{BASE}/orders/MPMH4F2").mock(return_value=httpx.Response(200, json={"data": {"id_order": "MPMH4F2", "ts_created_iso": "2026-09-20T10:00:00Z", "storefront": "de",
        "order_units": [{"id_order_unit": 1, "status": "need_to_be_sent", "price": 1999, "currency": "EUR"}]}}))
    res = await _server().call_tool("get_order", {"id": "MPMH4F2"})
    sc = res.structured_content
    assert sc["status"] == "need_to_be_sent" and sc["currency"] == "EUR" and sc["created_at"].startswith("2026-09-20")


@pytest.mark.asyncio
@respx.mock
async def test_bad_signature_is_an_auth_error_without_the_secret():
    respx.get(f"{BASE}/info/storefront").mock(return_value=httpx.Response(401, json={"message": "Signature mismatch kf-secret-64"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and "kf-secret-64" not in json.dumps(res.structured_content)
