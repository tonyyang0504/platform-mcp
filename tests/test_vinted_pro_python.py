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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "vinted_pro.json").read_text(encoding="utf-8"))
API = "https://pro-public-sandbox.svc.vinted.com"
CREDS = {"access_key": "foo-access", "signing_key": "bar-signing-secret", "api_host": "pro-public-sandbox.svc.vinted.com"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _check(req, method):
    m = re.fullmatch(r"t=(\d{10}),v1=([0-9a-f]{64})", req.headers["X-Vpi-Hmac-Sha256"])
    assert m and req.headers["X-Vpi-Access-Key"] == "foo-access"
    path = req.url.raw_path.decode()
    payload = f"{m.group(1)}.{method}.{path}.foo-access.{req.content.decode()}"
    assert m.group(2) == hmac.new(b"bar-signing-secret", payload.encode(), hashlib.sha256).hexdigest()


@pytest.mark.asyncio
@respx.mock
async def test_me_is_signed_over_path_with_query():
    route = respx.get(f"{API}/api/v1/items").mock(return_value=httpx.Response(200, json={"items": []}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["end_listing", "list_orders", "me"]
    assert (await server.call_tool("me", {})).is_error is False
    _check(route.calls.last.request, "GET")


@pytest.mark.asyncio
@respx.mock
async def test_delete_item_signs_the_body():
    route = respx.delete(f"{API}/api/v1/items").mock(return_value=httpx.Response(202, json={"items": [{"accepted": True, "item_id": "7f0c1b9e-1111-2222-3333-444455556666"}]}))
    res = await _server().call_tool("end_listing", {"listing_id": "7f0c1b9e-1111-2222-3333-444455556666"})
    assert res.is_error is False and res.structured_content["status"] == "delete_requested"
    req = route.calls.last.request
    assert json.loads(req.content) == {"item_ids": ["7f0c1b9e-1111-2222-3333-444455556666"]}
    _check(req, "DELETE")


@pytest.mark.asyncio
@respx.mock
async def test_orders_and_bad_signature():
    respx.get(f"{API}/api/v1/orders").mock(return_value=httpx.Response(200, json={"orders": [{"id": 998877, "status": "READY_TO_BE_SHIPPED", "created_at": "2026-09-20T10:00:00Z"}]}))
    res = await _server().call_tool("list_orders", {})
    assert res.structured_content["orders"][0] == {"id": "998877", "status": "READY_TO_BE_SHIPPED", "created_at": "2026-09-20T10:00:00Z", "raw": {"id": 998877, "status": "READY_TO_BE_SHIPPED", "created_at": "2026-09-20T10:00:00Z"}}
    respx.get(f"{API}/api/v1/orders").mock(return_value=httpx.Response(401, json={"error": "INVALID_HMAC_SIGNATURE"}))
    res = await _server().call_tool("list_orders", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
