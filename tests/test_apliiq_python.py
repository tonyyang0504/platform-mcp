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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "apliiq.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"app_id": "APP1", "shared_secret": "s3cr3t-shared"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_are_read_only_without_create_order():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_order", "get_product", "list_products", "me", "track"]


@pytest.mark.asyncio
@respx.mock
async def test_requests_carry_the_x_apliiq_auth_hmac_header():
    route = respx.get("https://api.apliiq.com/v1/Product").mock(return_value=httpx.Response(200, json=[
        {"Id": 162, "Name": "Womens T-Shirt", "Code": "womens_womens-t-shirt", "SKU": "6004", "Price": 11.5, "Currency_Code": "USD", "Sizes": [{"Id": 6, "Name": "s"}]}]))
    res = await _server().call_tool("list_products", {})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "162" and p["sku"] == "6004" and p["currency"] == "USD"
    auth = route.calls.last.request.headers["Authorization"]
    scheme, _, rest = auth.partition(" ")
    rts, sig, appid, state = rest.split(":")
    assert scheme == "x-apliiq-auth" and appid == "APP1" and state.isdigit()
    expected = base64.b64encode(hmac.new(b"s3cr3t-shared", f"APP1{rts}{state}".encode(), hashlib.sha256).digest()).decode()
    assert sig == expected


@pytest.mark.asyncio
@respx.mock
async def test_get_order_and_track_read_the_shipment_notices():
    respx.get("https://api.apliiq.com/v1/Order/426090").mock(return_value=httpx.Response(200, json=[
        {"OrderId": 426090, "OrderDate": "2023-08-14T00:00:00", "Status": "Shipped", "SN": [
            {"Helptext": "your package shipped on 08/18/2023", "Carrier": "https://tools.usps.com/go/TrackConfirmAction?tLabels=9400", "Service": "USPS First Class Mail", "TrackingNumber": "9400111", "Items": []}]}]))
    s = _server()
    res = await s.call_tool("get_order", {"id": "426090"})
    assert res.structured_content["status"] == "Shipped" and res.structured_content["tracking_number"] == "9400111"
    tr = await s.call_tool("track", {"order_id": "426090"})
    assert tr.structured_content["events"][0]["carrier"] == "USPS First Class Mail"


@pytest.mark.asyncio
@respx.mock
async def test_unauthorized_is_an_auth_error_without_the_secret():
    respx.get("https://api.apliiq.com/v1/Order").mock(return_value=httpx.Response(401, text="bad signature for s3cr3t-shared"))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "s3cr3t-shared" not in json.dumps(res.structured_content)
