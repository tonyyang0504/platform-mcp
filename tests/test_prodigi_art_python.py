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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "prodigi_art.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "k"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_order", "get_order", "get_product", "me", "quote_shipping"]  # no catalogue browse, no tracking endpoint
    gp = next(t for t in tools if t.name == "get_product")
    assert gp.annotations.read_only_hint is True and gp.input_schema["required"] == ["id"] and gp.meta["platform_mcp/endpoint"] == "/products/{id}"
    co = next(t for t in tools if t.name == "create_order")
    assert co.annotations.destructive_hint is True


@pytest.mark.asyncio
@respx.mock
async def test_get_order_maps_the_order_stage_and_tracking():
    # prodigi.com/print-api/docs/reference: GET /v4.0/Orders/{id} -> {outcome, order{id, created, status{stage}, shipments[{tracking{number,url}}]}}
    respx.get("https://api.prodigi.com/v4.0/Orders/ord_840797").mock(return_value=httpx.Response(200, json={
        "outcome": "Ok",
        "order": {"id": "ord_840797", "created": "2021-03-11T14:40:05.12Z", "status": {"stage": "Complete", "issues": []}, "charges": [],
                  "shipments": [{"carrier": {"name": "royalmail", "service": "Standard"}, "tracking": {"number": "RM123", "url": "https://track.example/RM123"}, "items": ["ori_926887"]}],
                  "items": [{"id": "ori_926887", "sku": "GLOBAL-CFPM-16X20", "copies": 1}]}}))
    res = await _server().call_tool("get_order", {"id": "ord_840797"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "ord_840797" and sc["status"] == "Complete" and sc["tracking_number"] == "RM123" and sc["created_at"].startswith("2021-03-11")
    assert respx.calls.last.request.headers["X-API-Key"] == "k"


@pytest.mark.asyncio
@respx.mock
async def test_get_product_maps_the_sku_record():
    respx.get("https://api.prodigi.com/v4.0/products/GLOBAL-CAN-10X10").mock(return_value=httpx.Response(200, json={
        "outcome": "Ok", "product": {"sku": "GLOBAL-CAN-10X10", "description": "Standard canvas on quality stretcher bar, 25x25cm",
                                     "productDimensions": {"width": 10.0, "height": 10.0, "units": "in"}, "attributes": {"wrap": ["Black", "White"]}, "variants": []}}))
    res = await _server().call_tool("get_product", {"id": "GLOBAL-CAN-10X10"})
    assert res.is_error is False and res.structured_content["id"] == "GLOBAL-CAN-10X10" and res.structured_content["title"].startswith("Standard canvas")


@pytest.mark.asyncio
@respx.mock
async def test_unknown_order_is_a_not_found_tool_error():
    respx.get("https://api.prodigi.com/v4.0/Orders/nope").mock(return_value=httpx.Response(404, json={"outcome": "NotFound"}))
    res = await _server().call_tool("get_order", {"id": "nope"})
    assert res.is_error is True and res.structured_content["error"] == "not_found" and res.structured_content["http_status"] == 404


@pytest.mark.asyncio
@respx.mock
async def test_quote_shipping_posts_a_one_item_quote():
    # prodigi.com/print-api/docs/reference/#create-quote: POST /v4.0/quotes -> {outcome, quotes[{shipmentMethod, costSummary{items, shipping}}]}
    route = respx.post("https://api.prodigi.com/v4.0/quotes").mock(return_value=httpx.Response(200, json={"outcome": "Created", "quotes": [
        {"shipmentMethod": "Budget", "costSummary": {"items": {"amount": "79.35", "currency": "GBP"}, "shipping": {"amount": "19.46", "currency": "GBP"}}, "shipments": []}]}))
    res = await _server().call_tool("quote_shipping", {"product_id": "GLOBAL-FAP-10x10", "country": "GB", "quantity": 5})
    assert res.is_error is False
    opt = res.structured_content["options"][0]
    assert opt["shipping_method"] == "Budget" and opt["shipping_cost"] == "19.46" and opt["currency"] == "GBP"
    assert json.loads(route.calls.last.request.content) == {"destinationCountryCode": "GB", "items": [{"sku": "GLOBAL-FAP-10x10", "copies": 5, "assets": [{"printArea": "default"}]}]}
