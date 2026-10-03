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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "orosy.json").read_text(encoding="utf-8"))
API = "https://wholesale-api.orosy.com"
PID = "3f0b8d8e-1c7e-4a39-9d1e-2b8f0c7a1d11"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {"api_key": "orosy_live_SECRET"}, 50, "test"))


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_order", "get_product", "list_products", "me", "quote_shipping", "track"]
    assert all(t.annotations.read_only_hint for t in tools)


@pytest.mark.asyncio
@respx.mock
async def test_list_products_searches_with_q_and_pages():
    respx.get(f"{API}/v1/products").mock(return_value=httpx.Response(200, json={
        "items": [{"product_id": PID, "title": "今治タオル フェイスタオル", "brand": "Imabari", "images": ["https://cdn.orosy.com/p/1.jpg"],
                   "category": "生活雑貨/タオル", "delivery_group": "G1", "min_buyer_price": 480, "max_buyer_price": 520, "min_retail_price": 1200,
                   "variation_count": 3, "orderable": True}],
        "page": 2, "per_page": 1, "total": 5}))
    res = await _server().call_tool("list_products", {"query": "タオル", "page": 2, "limit": 1})
    sc = res.structured_content
    assert sc["products"][0]["id"] == PID and sc["products"][0]["price"] == 480 and sc["products"][0]["image_url"] == "https://cdn.orosy.com/p/1.jpg"
    assert sc["total"] == 5 and sc["next_page"] == 3
    req = respx.calls.last.request
    assert req.url.params["q"] == "タオル" and req.url.params["page"] == "2" and req.url.params["per_page"] == "1"
    assert req.headers["Authorization"] == "Bearer orosy_live_SECRET"


@pytest.mark.asyncio
@respx.mock
async def test_quote_shipping_reads_cross_border_eligibility():
    respx.get(f"{API}/v1/cross-border/eligibility").mock(return_value=httpx.Response(200, json={
        "dest": "US", "items": [{"product_id": PID, "not_found": False, "logistics": {"status": "ok", "reasons": []},
                                 "shipping": {"status": "quoted", "amount": 2400, "currency": "JPY", "basis": "per_item", "notes": []}}]}))
    res = await _server().call_tool("quote_shipping", {"product_id": PID, "country": "US", "quantity": 2})
    opt = res.structured_content["options"][0]
    assert opt["status"] == "quoted" and opt["amount"] == 2400 and opt["logistics_status"] == "ok"
    q = respx.calls.last.request.url.params
    assert q["dest"] == "US" and q["product_ids"] == PID


@pytest.mark.asyncio
@respx.mock
async def test_get_order_and_track_read_shipments():
    order = {"order_id": "o-1", "status": "confirmed", "created_at": "2026-09-20T01:00:00Z", "breakdown": {"total": 10560, "currency": "JPY", "shipping_fee": 800},
             "payment": {"status": "succeeded"},
             "groups": [{"group_code": "G1", "shipments": [{"shipment_id": "s1", "status": "shipped", "trackings": [{"tracking_no": "1234-5678", "carrier": "ヤマト運輸"}], "shipped_at": "2026-09-21T02:00:00Z"}]}]}
    respx.get(f"{API}/v1/orders/o-1").mock(return_value=httpx.Response(200, json=order))
    got = (await _server().call_tool("get_order", {"id": "o-1"})).structured_content
    assert got["status"] == "confirmed" and got["total"] == 10560 and got["tracking_number"] == "1234-5678"
    ev = (await _server().call_tool("track", {"order_id": "o-1"})).structured_content["events"]
    assert ev[0]["tracking_number"] == "1234-5678" and ev[0]["status"] == "shipped"


@pytest.mark.asyncio
@respx.mock
async def test_bad_key_is_an_auth_error_without_the_key():
    respx.get(f"{API}/v1/me").mock(return_value=httpx.Response(401, json={"error": "invalid api key orosy_live_SECRET"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "orosy_live_SECRET" not in json.dumps(res.structured_content)
