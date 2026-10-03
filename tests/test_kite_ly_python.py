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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "kite_ly.json").read_text(encoding="utf-8"))
BASE = "https://api.kite.ly"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key_pair": "pk_test:sk-secret-1"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_order", "get_order", "me", "track"]


@pytest.mark.asyncio
@respx.mock
async def test_create_order_maps_the_address_and_jobs():
    route = respx.post(f"{BASE}/v4.0/print/").mock(return_value=httpx.Response(200, json={"print_order_id": "PS96-996634811"}))
    res = await _server().call_tool("create_order", {
        "items": [{"template_id": "i6_case", "assets": ["https://img.example/1.jpg"]}],
        "shipping_address": {"recipient_name": "Deon Botha", "address_line_1": "Eastcastle House", "city": "London", "county_state": "Greater London", "postcode": "W1W 8DH", "country_code": "GBR", "phone": "+44 784297 1234", "email": "d@example.com"}})
    assert res.is_error is False and res.structured_content["id"] == "PS96-996634811"
    req = route.calls.last.request
    assert req.headers["Authorization"] == "ApiKey pk_test:sk-secret-1"
    body = json.loads(req.content)
    assert body["shipping_address"] == {"recipient_name": "Deon Botha", "address_line_1": "Eastcastle House", "city": "London", "county_state": "Greater London", "postcode": "W1W 8DH", "country_code": "GBR"}
    assert body["customer_phone"] == "+44 784297 1234" and body["customer_email"] == "d@example.com" and body["jobs"][0]["template_id"] == "i6_case"


@pytest.mark.asyncio
@respx.mock
async def test_get_order_and_track_read_the_jobs():
    respx.get(f"{BASE}/v4.0/order/PS320-236374811").mock(return_value=httpx.Response(200, json={
        "dispatch_status": "In Print Queue", "order_id": "PS320-236374811", "status": "Processed", "time_submitted": "2015-11-16T20:04:12.209495",
        "jobs": [{"job_id": "PS320-23637481101-S9-MAGNETS-M", "shipped_time": None, "status": "Received by Printer", "template": {"id": "s9_magnets_mini"}}]}))
    s = _server()
    res = await s.call_tool("get_order", {"id": "PS320-236374811"})
    assert res.structured_content["status"] == "Processed" and res.structured_content["dispatch_status"] == "In Print Queue"
    tr = await s.call_tool("track", {"order_id": "PS320-236374811"})
    assert tr.structured_content["events"][0]["template_id"] == "s9_magnets_mini"


@pytest.mark.asyncio
@respx.mock
async def test_schema_error_is_upstream_without_the_secret():
    respx.post(f"{BASE}/v4.0/print/").mock(return_value=httpx.Response(400, json={"error": {"code": "01", "message": "JSON schema error for pk_test:sk-secret-1"}}))
    res = await _server().call_tool("create_order", {"items": [], "shipping_address": {}})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
    assert "sk-secret-1" not in json.dumps(res.structured_content)
