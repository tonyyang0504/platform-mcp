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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "dropshipzone.json").read_text(encoding="utf-8"))
BASE = "https://api.dropshipzone.com.au"
CREDS = {"email": "api@example.com", "password": "pw"}


def _server(creds=None):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds or CREDS, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
@respx.mock
async def test_login_then_jwt_header_and_list_products_params():
    login = respx.post(f"{BASE}/auth").mock(return_value=httpx.Response(200, json={"iat": 1569986936, "exp": 1570206536, "token": "T0K"}))
    respx.get(f"{BASE}/v2/products").mock(return_value=httpx.Response(200, json={
        "result": [{"entity_id": 186573, "sku": "V201-W12898984", "title": "12V Car Fan Heater", "price": 29.31, "currency": "AUD", "stock_qty": 44,
                    "gallery": ["https://cdn.test/0.png"], "website_url": "https://dsz.test/p.html", "RrpPrice": 58.61}],
        "total": 91, "total_pages": 5, "current_page": 1}))
    res = await _server().call_tool("list_products", {"query": "heater", "category": "722"})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "V201-W12898984" and p["price"] == 29.31 and p["stock"] == 44 and p["image_url"] == "https://cdn.test/0.png"
    assert res.structured_content["total"] == 91
    assert json.loads(login.calls.last.request.content) == {"email": "api@example.com", "password": "pw"}
    req = respx.calls.last.request
    assert req.headers["Authorization"] == "jwt T0K"
    assert req.url.params["keywords"] == "heater" and req.url.params["category_id"] == "722" and req.url.params["limit"] == "40" and req.url.params["page_no"] == "1"


@pytest.mark.asyncio
@respx.mock
async def test_create_order_flattens_the_consignee_and_reports_errmsg():
    respx.post(f"{BASE}/auth").mock(return_value=httpx.Response(200, json={"token": "T0K"}))
    route = respx.post(f"{BASE}/placingOrder").mock(return_value=httpx.Response(200, json=[{"status": -1, "serial_number": "P02100689", "errmsg": "The postcode cannot be found"}]))
    addr = {"first_name": "John", "last_name": "Baker", "address1": "add1", "address2": "add2", "suburb": "Eugowra", "state": "NSW", "postcode": "2806", "telephone": "0412345678", "comment": "c"}
    res = await _server().call_tool("create_order", {"items": [{"sku": "MOC-09M-2P-BK", "qty": 3}], "shipping_address": addr})
    sc = res.structured_content
    assert sc["id"] == "P02100689" and sc["result_status"] == -1 and sc["errmsg"] == "The postcode cannot be found"
    body = json.loads(route.calls.last.request.content)
    assert body["first_name"] == "John" and body["suburb"] == "Eugowra" and body["postcode"] == "2806" and body["order_items"] == [{"sku": "MOC-09M-2P-BK", "qty": 3}]
    assert len(body["your_order_no"]) == 36 and "shipping_address" not in body


@pytest.mark.asyncio
@respx.mock
async def test_track_reads_the_shipments_of_the_order():
    respx.post(f"{BASE}/auth").mock(return_value=httpx.Response(200, json={"token": "T0K"}))
    respx.get(f"{BASE}/orders").mock(return_value=httpx.Response(200, json={"status": 1, "data": [
        {"increment_id": "100000001", "status": "complete", "shipment": [{"track_number": "1232132121", "title": "Aus Post", "created_at": "2022-01-04 16:23:04"}]}], "total": 1}))
    res = await _server().call_tool("track", {"order_id": "100000001"})
    assert res.structured_content["events"][0]["tracking_number"] == "1232132121" and res.structured_content["events"][0]["carrier"] == "Aus Post"
    assert respx.calls.last.request.url.params["order_ids"] == "100000001"


@pytest.mark.asyncio
@respx.mock
async def test_refused_login_is_an_auth_error():
    respx.post(f"{BASE}/auth").mock(return_value=httpx.Response(401, json={"code": "Unauthorized"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
