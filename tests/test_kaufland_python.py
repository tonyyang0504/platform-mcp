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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "kaufland.json").read_text(encoding="utf-8"))
API = "https://sellerapi.kaufland.com/v2"


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], {"client_key": "ck-32", "secret_key": "kf-secret-64", "storefront": "de"}, 50, "test")
    return build_server(SPEC, transport=t)


def _sig_ok(req, method):
    ts = req.headers["Shop-Timestamp"]
    body = req.content.decode()
    expected = hmac.new(b"kf-secret-64", f"{method}\n{req.url}\n{body}\n{ts}".encode(), hashlib.sha256).hexdigest()
    return req.headers["Shop-Client-Key"] == "ck-32" and req.headers["Shop-Signature"] == expected


@pytest.mark.asyncio
async def test_tools():
    assert sorted(t.name for t in await _server().list_tools()) == ["end_listing", "list_orders", "mark_shipped", "me", "set_inventory"]


@pytest.mark.asyncio
@respx.mock
async def test_set_inventory_patches_amount_signed_over_uri_and_body():
    route = respx.patch(f"{API}/units/3001").mock(return_value=httpx.Response(200, json={"data": {"id_unit": 3001, "status": "AVAILABLE", "amount": 12}}))
    res = await _server().call_tool("set_inventory", {"listing_id": "3001", "quantity": 12})
    assert res.is_error is False and res.structured_content["status"] == "AVAILABLE"
    req = route.calls.last.request
    assert req.url.params["storefront"] == "de" and json.loads(req.content) == {"amount": 12}
    assert _sig_ok(req, "PATCH")


@pytest.mark.asyncio
@respx.mock
async def test_list_orders_reads_order_units():
    route = respx.get(f"{API}/order-units").mock(return_value=httpx.Response(200, json={"data": [
        {"id_order_unit": 9001, "id_order": "MMXX1", "status": "need_to_be_sent", "currency": "EUR", "price": 1999, "ts_created_iso": "2026-09-20T10:00:00Z"}],
        "pagination": {"offset": 0, "limit": 30, "total": 1}}))
    res = await _server().call_tool("list_orders", {"status": "need_to_be_sent", "since": "2026-09-01T00:00:00Z"})
    o = res.structured_content["orders"][0]
    assert o["id"] == "9001" and o["status"] == "need_to_be_sent" and o["currency"] == "EUR" and res.structured_content["total"] == 1
    p = route.calls.last.request.url.params
    assert p["status"] == "need_to_be_sent" and p["ts_created_from_iso"] == "2026-09-01T00:00:00Z" and p["storefront"] == "de"
    assert _sig_ok(route.calls.last.request, "GET")


@pytest.mark.asyncio
@respx.mock
async def test_mark_shipped_sends_order_unit_and_handles_204():
    route = respx.patch(f"{API}/order-units/9001/send").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("mark_shipped", {"order_id": "9001", "carrier": "DHL", "tracking_number": "00340434161234567890"})
    assert res.is_error is False and res.structured_content["status"] == "sent"
    assert json.loads(route.calls.last.request.content) == {"tracking_numbers": "00340434161234567890", "carrier_code": "DHL"}
    assert _sig_ok(route.calls.last.request, "PATCH")
