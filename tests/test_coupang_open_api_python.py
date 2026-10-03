import hashlib
import hmac
import json
import re
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "coupang_open_api.json").read_text(encoding="utf-8"))
BASE = "https://api-gateway.coupang.com"
PRODUCTS = f"{BASE}/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"access_key": "AK1", "secret_key": "cp-secret-55", "vendor_id": "A00012345"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_are_seller_side_reads():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_order", "get_product", "list_products", "me", "track"]


@pytest.mark.asyncio
@respx.mock
async def test_list_products_is_signed_with_the_cea_hmac_header():
    route = respx.get(PRODUCTS).mock(return_value=httpx.Response(200, json={"code": "SUCCESS", "message": "", "nextToken": "2", "data": [
        {"sellerProductId": 239092172, "sellerProductName": "R07 헬로키티 미니낚시놀이", "displayCategoryCode": 77413, "brand": "상세설명별도참조", "statusName": "승인완료"}]}))
    res = await _server().call_tool("list_products", {"page": 1, "limit": 5})
    assert res.structured_content["products"][0]["id"] == "239092172"
    req = route.calls.last.request
    query = req.url.query.decode()
    assert "vendorId=A00012345" in query and "maxPerPage=5" in query and "nextToken=1" in query
    m = re.fullmatch(r"CEA algorithm=HmacSHA256, access-key=AK1, signed-date=(\d{6}T\d{6}Z), signature=([0-9a-f]{64})", req.headers["Authorization"])
    assert m
    msg = f"{m.group(1)}GET/v2/providers/seller_api/apis/api/v1/marketplace/seller-products{query}"
    assert m.group(2) == hmac.new(b"cp-secret-55", msg.encode(), hashlib.sha256).hexdigest()


@pytest.mark.asyncio
@respx.mock
async def test_get_order_fills_the_vendor_id_in_the_path():
    respx.get(f"{BASE}/v2/providers/openapi/apis/api/v5/vendors/A00012345/500000596/ordersheets").mock(return_value=httpx.Response(200, json={
        "code": "200", "message": "OK", "data": [{"shipmentBoxId": 642538970006401429, "orderId": 500000596, "orderedAt": "2025-01-15T14:17:13", "status": "DELIVERING",
                                                  "deliveryCompanyName": "CJ 대한통운", "invoiceNumber": "123456789", "inTrasitDateTime": "2025-01-16 10:00:00"}]}))
    s = _server()
    res = await s.call_tool("get_order", {"id": "500000596"})
    sc = res.structured_content
    assert sc["id"] == "500000596" and sc["status"] == "DELIVERING" and sc["tracking_number"] == "123456789"
    tr = await s.call_tool("track", {"order_id": "500000596"})
    assert tr.structured_content["events"][0]["carrier"] == "CJ 대한통운"


@pytest.mark.asyncio
@respx.mock
async def test_rejected_signature_is_an_auth_error_without_the_secret():
    respx.get(PRODUCTS).mock(return_value=httpx.Response(401, json={"code": "ERROR", "message": "Invalid signature for key cp-secret-55"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "cp-secret-55" not in json.dumps(res.structured_content)
