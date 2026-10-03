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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "kaspi_shop_api.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"token": "kaspi-tok-1"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_order_lookup_is_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_order", "me"]


@pytest.mark.asyncio
@respx.mock
async def test_get_order_filters_by_code_with_the_auth_token():
    # guide.kaspi.kz/partner/ru/shop/api/orders: GET /v2/orders?filter[orders][code]= -> {data[{type: orders, id, attributes{code, totalPrice, status, state}}]}
    route = respx.get("https://kaspi.kz/shop/api/v2/orders").mock(return_value=httpx.Response(200, json={"data": [{"type": "orders", "id": "b3JkZXI", "attributes": {
        "code": "123456789", "totalPrice": 4000.0, "status": "ACCEPTED_BY_MERCHANT", "state": "DELIVERY", "creationDate": 1706608613252, "deliveryMode": "DELIVERY_LOCAL"}}], "meta": {"totalCount": 1}}))
    res = await _server().call_tool("get_order", {"id": "123456789"})
    sc = res.structured_content
    assert sc["id"] == "123456789" and sc["total"] == 4000.0 and sc["currency"] == "KZT" and sc["status"] == "ACCEPTED_BY_MERCHANT"
    req = route.calls.last.request
    assert req.headers["X-Auth-Token"] == "kaspi-tok-1" and req.headers["Content-Type"] == "application/vnd.api+json"
    assert req.url.params["filter[orders][code]"] == "123456789"


@pytest.mark.asyncio
@respx.mock
async def test_unknown_code_is_not_found_and_bad_token_hides_the_secret():
    respx.get("https://kaspi.kz/shop/api/v2/orders").mock(return_value=httpx.Response(200, json={"data": [], "meta": {"totalCount": 0}}))
    res = await _server().call_tool("get_order", {"id": "0"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"
    respx.get("https://kaspi.kz/shop/api/products/import/schema").mock(return_value=httpx.Response(401, text="bad token kaspi-tok-1"))
    me = await _server().call_tool("me", {})
    assert me.is_error is True and me.structured_content["error"] == "auth_error" and "kaspi-tok-1" not in json.dumps(me.structured_content)
