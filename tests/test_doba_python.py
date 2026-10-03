import base64
import json
import sys
from pathlib import Path

import httpx
import pytest
import respx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "doba.json").read_text(encoding="utf-8"))
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
DER = KEY.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
PEM = "-----BEGIN PRIVATE KEY-----\\n" + base64.b64encode(DER).decode() + "\\n-----END PRIVATE KEY-----"  # one line, as env vars carry it
CREDS = {"app_key": "20201103773281123722592256", "private_key": PEM, "platform_id": "3"}
BASE = "https://openapi.doba.com"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _check_sign(request):
    h = request.headers
    assert h["appKey"] == CREDS["app_key"] and h["signType"] == "rsa2" and h["timestamp"].isdigit() and len(h["timestamp"]) == 13
    content = f"appKey={CREDS['app_key']}&signType=rsa2&timestamp={h['timestamp']}".encode()
    KEY.public_key().verify(base64.b64decode(h["sign"]), content, padding.PKCS1v15(), hashes.SHA256())


@pytest.mark.asyncio
@respx.mock
async def test_spu_list_is_rsa_signed_in_headers():
    route = respx.get(url__startswith=f"{BASE}/api/goods/doba/spu/list").mock(return_value=httpx.Response(200, json={"responseCode": "000000", "responseMessage": "Success", "businessData": {
        "businessStatus": "000000", "data": {"totalQuantity": 100, "goodsList": [{"spuId": "miUpfVDmedjr", "title": "Garlic01", "minPrice": "15", "maxPrice": "20", "pictureUrl": "https://image.doba.com/x.jpg", "inventory": "10"}]}}}))
    res = await _server().call_tool("list_products", {"query": "garlic", "limit": 10, "page": 2})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "miUpfVDmedjr" and p["price"] == "15" and p["currency"] == "USD" and res.structured_content["total"] == 100
    req = route.calls[0].request
    assert dict(req.url.params) == {"keyword": "garlic", "pageNumber": "2", "pageSize": "10"}
    _check_sign(req)


@pytest.mark.asyncio
@respx.mock
async def test_get_product_maps_the_first_variant_warehouse():
    route = respx.get(url__startswith=f"{BASE}/api/goods/doba/spu/detail").mock(return_value=httpx.Response(200, json={"responseCode": "000000", "businessData": {"data": [{
        "spuId": "ivUfpgDdAOoh", "title": "Marker Boards", "children": [{"currencyId": "USD", "skuUrl": "https://www.doba.com/product/x", "skuPicList": ["https://image.doba.com/a.jpg"],
                                                                           "stocks": [{"itemNo": "D0102HEVPDA", "availableNum": 100, "sellingPrice": 150.32}]}]}]}}))
    res = await _server().call_tool("get_product", {"id": "ivUfpgDdAOoh"})
    sc = res.structured_content
    assert res.is_error is False and sc["sku"] == "D0102HEVPDA" and sc["price"] == 150.32 and sc["stock"] == 100
    assert route.calls[0].request.url.params["spuId"] == "ivUfpgDdAOoh"
    _check_sign(route.calls[0].request)


@pytest.mark.asyncio
@respx.mock
async def test_create_order_builds_the_import_order_body():
    route = respx.post(f"{BASE}/api/order/doba/importOrder").mock(return_value=httpx.Response(200, json={"responseCode": "000000", "businessData": {"businessStatus": "000000", "data": {
        "orderSuccessResList": [{"ordBusiId": 101704080100167581, "ordBatchId": 372103318541472961, "totalPay": 111, "currency": "USD", "orderPayURL": "https://pay.doba.com/x"}]}}}))
    addr = {"name": "Ann Lee", "addr1": "1 Main St", "city": "New York", "provinceCode": "NY", "countryCode": "US", "zip": "10041", "telephone": "2125550100"}
    items = [{"itemNo": "D0102HEVPDA", "quantityOrdered": "2", "shippingMethodId": "WAfpUKUWyPar"}]
    res = await _server().call_tool("create_order", {"items": items, "shipping_address": addr})
    assert res.is_error is False and res.structured_content["id"] == "101704080100167581" and res.structured_content["total"] == 111
    body = json.loads(route.calls[0].request.content)
    assert body == {"billingAddress": addr, "openApiImportDSOrderList": [{"orderNumber": "1", "dsPlatformId": "3", "shippingAddress": addr, "goodsDetailDTOList": items}]}
    _check_sign(route.calls[0].request)


@pytest.mark.asyncio
@respx.mock
async def test_quote_track_and_failed_response_code():
    respx.post(f"{BASE}/api/shipping/doba/cost/goods").mock(return_value=httpx.Response(200, json={"responseCode": "000000", "businessData": [{"data": {"itemNo": "D0102HEVPDA", "costs": [
        {"shippingMethodId": "WAfpUKUWyPar", "shipName": "UPS Ground", "shipFee": 13.2, "currencyId": "USD", "shipTime": "1-5"}]}}]}))
    track = respx.post(f"{BASE}/api/order/doba/queryLogisTrack").mock(return_value=httpx.Response(200, json={"responseCode": "999999", "responseMessage": "Operate Fail."}))
    s = _server()
    q = await s.call_tool("quote_shipping", {"product_id": "D0102HEVPDA", "country": "US", "quantity": 2})
    assert q.is_error is False and q.structured_content["options"][0]["id"] == "WAfpUKUWyPar"
    t = await s.call_tool("track", {"order_id": "412104129113499481"})
    assert t.is_error is True
    assert json.loads(track.calls[0].request.content) == {"ordBusiId": "412104129113499481"}
