import hashlib
import hmac
import json
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "lazada_open_platform.json").read_text(encoding="utf-8"))
CREDS = {"app_key": "100132", "app_secret": "laz-secret-0123456789", "access_token": "50000601237osiQodfgbhs2iXplQ1f0dDfs9Wj0frtc3d1E2d0Nm", "domain": "sg"}
API = "https://api.lazada.sg/rest"


def _server(creds=None):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(creds or CREDS), 50, "test", envelope=a.get("envelope")))


def _check_sign(request, api_name):
    params = dict(parse_qsl(urlsplit(str(request.url)).query, keep_blank_values=True))
    sig = params.pop("sign")
    base = api_name + "".join(k + params[k] for k in sorted(params))
    assert sig == hmac.new(CREDS["app_secret"].encode(), base.encode(), hashlib.sha256).hexdigest().upper()
    assert params["app_key"] == "100132" and params["sign_method"] == "sha256" and params["access_token"] == CREDS["access_token"] and len(params["timestamp"]) == 13
    return params


@pytest.mark.asyncio
@respx.mock
async def test_signature_uses_the_api_name_without_the_rest_prefix():
    route = respx.get(url__startswith=f"{API}/order/get").mock(return_value=httpx.Response(200, json={"code": "0", "data": {
        "order_id": "16090", "statuses": ["pending"], "price": "99.00", "created_at": "2014-10-15 18:36:05 +0800", "order_number": "300034416"}, "request_id": "r"}))
    res = await _server().call_tool("get_order", {"id": "16090"})
    sc = res.structured_content
    assert res.is_error is False and sc["id"] == "16090" and sc["status"] == "pending" and sc["total"] == "99.00"
    params = _check_sign(route.calls[0].request, "/order/get")
    assert params["order_id"] == "16090"


@pytest.mark.asyncio
@respx.mock
async def test_list_products_first_sku_and_malaysia_gateway():
    route = respx.get(url__startswith="https://api.lazada.com.my/rest/products/get").mock(return_value=httpx.Response(200, json={"code": "0", "data": {"total_products": "10", "products": [
        {"item_id": "180226526", "attributes": {"name": "asd"}, "skus": [{"SellerSku": "39817:01:01", "price": 32, "quantity": 5, "Url": "https://www.lazada.com.my/x.html", "Images": ["http://x/1.jpg"]}]}]}}))
    res = await _server({**CREDS, "domain": "com.my"}).call_tool("list_products", {"limit": 10, "page": 3})
    p = res.structured_content["products"][0]
    assert res.is_error is False and p["id"] == "180226526" and p["sku"] == "39817:01:01" and p["price"] == 32 and p["stock"] == 5
    params = _check_sign(route.calls[0].request, "/products/get")
    assert params["filter"] == "all" and params["offset"] == "20" and params["limit"] == "10"


@pytest.mark.asyncio
@respx.mock
async def test_track_returns_packages():
    route = respx.get(url__startswith=f"{API}/logistic/order/trace").mock(return_value=httpx.Response(200, json={"code": "0", "result": {"success": "true", "module": [{"package_detail_info_list": [
        {"ofc_package_id": "FP032211046428116", "tracking_number": "NLXSG20300914", "logistic_detail_info_list": [{"title": "Packed by seller / warehouse", "event_time": "1625987646597"}]}]}]}}))
    res = await _server().call_tool("track", {"order_id": "16090"})
    ev = res.structured_content["events"][0]
    assert res.is_error is False and ev["tracking_number"] == "NLXSG20300914" and ev["latest"] == "Packed by seller / warehouse"
    _check_sign(route.calls[0].request, "/logistic/order/trace")


@pytest.mark.asyncio
@respx.mock
async def test_illegal_access_token_is_an_error():
    respx.get(url__startswith=f"{API}/seller/get").mock(return_value=httpx.Response(200, json={"type": "ISV", "code": "IllegalAccessToken", "message": "The specified access token is invalid or expired", "request_id": "r"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
