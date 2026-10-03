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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "bookvault.json").read_text(encoding="utf-8"))
BASE = "https://api.bookvault.app"


def _server(**extra):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "bv_k3y-secret", **extra}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_order", "get_order", "get_product", "list_products", "me"]
    co = next(t for t in tools if t.name == "create_order")
    assert co.annotations.destructive_hint is True


@pytest.mark.asyncio
@respx.mock
async def test_list_products_pages_the_title_library_with_basic_key():
    # api.bookvault.app swagger v4: GET /v4/titles?titlesPerPage=&pageNumber= -> {titles[{isbn, title, status{beautified}}], pagination{totalTitles}}
    route = respx.get(f"{BASE}/v4/titles").mock(return_value=httpx.Response(200, json={
        "titles": [{"isbn": "9781234567897", "title": "My Book", "status": {"status": "Live", "beautified": "Live"}, "titleType": "Standard"}],
        "pagination": {"currentPage": 2, "titlesPerPage": 10, "totalTitles": 11, "totalPages": 2}}))
    res = await _server().call_tool("list_products", {"page": 2, "limit": 10})
    sc = res.structured_content
    assert sc["products"][0]["id"] == "9781234567897" and sc["products"][0]["status"] == "Live" and sc["total"] == 11
    req = route.calls.last.request
    assert req.headers["Authorization"] == "basic bv_k3y-secret"
    assert req.url.params["titlesPerPage"] == "10" and req.url.params["pageNumber"] == "2"


@pytest.mark.asyncio
@respx.mock
async def test_create_order_builds_the_order_post_request():
    route = respx.post(f"{BASE}/v4/order").mock(return_value=httpx.Response(200, json={"podRef": 123456, "message": "Order created"}))
    res = await _server(partner="Bookvault_UK").call_tool("create_order", {
        "items": [{"lineNumber": 1, "isbn": "9781234567897", "quantity": 2}],
        "shipping_address": {"addressee": "Jo Bloggs", "address1": "1 High St", "town": "Norwich", "countryCode": "GB", "postCode": "NR1 1AA"},
        "shipping_option": "Cheapest"})
    assert res.is_error is False and res.structured_content["id"] == "123456"
    body = json.loads(route.calls.last.request.content)
    assert body["partner"] == "Bookvault_UK" and body["dispatchRequest"] == {"requestedService": "Cheapest"}
    assert body["orderLines"][0]["isbn"] == "9781234567897" and body["address"]["postCode"] == "NR1 1AA" and len(body["docRef"]) == 36


@pytest.mark.asyncio
@respx.mock
async def test_refused_key_is_an_auth_error_without_the_key():
    respx.get(f"{BASE}/v4/account").mock(return_value=httpx.Response(401, json={"message": "Invalid key bv_k3y-secret"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "bv_k3y-secret" not in json.dumps(res.structured_content)
