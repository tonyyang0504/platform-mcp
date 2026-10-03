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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "coupang.json").read_text(encoding="utf-8"))
VI = "https://api-gateway.coupang.com/v2/providers/seller_api/apis/api/v1/marketplace/vendor-items"


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], {"access_key": "AK1", "secret_key": "cp-secret-55", "vendor_id": "A00012345"}, 50, "test", envelope=a["envelope"])
    return build_server(SPEC, transport=t)


def _check_sig(req, method):
    m = re.fullmatch(r"CEA algorithm=HmacSHA256, access-key=AK1, signed-date=(\d{6}T\d{6}Z), signature=([0-9a-f]{64})", req.headers["Authorization"])
    assert m
    msg = f"{m.group(1)}{method}{req.url.path}{req.url.query.decode()}"
    assert m.group(2) == hmac.new(b"cp-secret-55", msg.encode(), hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_tools():
    assert sorted(t.name for t in await _server().list_tools()) == ["end_listing", "me", "set_inventory", "update_listing"]


@pytest.mark.asyncio
@respx.mock
async def test_set_inventory_puts_quantity_in_the_signed_path():
    route = respx.put(f"{VI}/3572784698/quantities/15").mock(return_value=httpx.Response(200, json={"code": "SUCCESS", "message": ""}))
    res = await _server().call_tool("set_inventory", {"listing_id": "3572784698", "quantity": 15})
    assert res.is_error is False and res.structured_content["status"] == "quantity_updated"
    _check_sig(route.calls.last.request, "PUT")


@pytest.mark.asyncio
@respx.mock
async def test_update_listing_changes_price_with_force_flag_signed_over_the_query():
    route = respx.put(f"{VI}/3572784698/prices/49000").mock(return_value=httpx.Response(200, json={"code": "SUCCESS", "message": ""}))
    res = await _server().call_tool("update_listing", {"listing_id": "3572784698", "price": 49000})
    assert res.is_error is False and res.structured_content["status"] == "price_updated"
    req = route.calls.last.request
    assert req.url.params["forceSalePriceUpdate"] == "true"
    _check_sig(req, "PUT")


@pytest.mark.asyncio
@respx.mock
async def test_error_code_in_200_body_is_an_error():
    respx.put(f"{VI}/3572784698/sales/stop").mock(return_value=httpx.Response(200, json={"code": "ERROR", "message": "판매중지에 실패했습니다. [vendoritemid 3572784698 not found]"}))
    res = await _server().call_tool("end_listing", {"listing_id": "3572784698"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
