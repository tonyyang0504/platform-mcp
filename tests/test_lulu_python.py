import base64
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "lulu.json").read_text(encoding="utf-8"))
API = "https://api.lulu.com"
TOKEN_URL = "https://api.lulu.com/auth/realms/glasstree/protocol/openid-connect/token"


def _server(extra=None):
    a = SPEC["adapter"]
    creds = {"client_id": "ck", "client_secret": "csSECRET", **(extra or {})}
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], creds, 50, "test"))


def _tok():
    return httpx.Response(200, json={"access_token": "eyJ.acc", "expires_in": 3600, "token_type": "Bearer"})


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["create_order", "get_order", "me", "track"]
    co = next(t for t in tools if t.name == "create_order")
    assert co.annotations.destructive_hint is True and "SPEND MONEY" in co.description


@pytest.mark.asyncio
@respx.mock
async def test_client_credentials_then_create_print_job():
    token = respx.post(TOKEN_URL).mock(return_value=_tok())
    route = respx.post(f"{API}/print-jobs/").mock(return_value=httpx.Response(201, json={
        "id": 1, "status": {"name": "CREATED", "message": "Print-job is currently being validated"}, "date_created": "2017-08-07T08:47:26.485456Z",
        "costs": {"currency": "USD", "total_cost_incl_tax": None}, "line_items": [{"id": 1, "status": {"name": "CREATED", "messages": {}}}], "shipping_level": "MAIL"}))
    items = [{"title": "My Book", "quantity": 20, "printable_normalization": {"pod_package_id": "0600X0900.BW.STD.PB.060UW444.MXX",
              "cover": {"source_url": "https://example.com/cover.pdf"}, "interior": {"source_url": "https://example.com/interior.pdf"}}}]
    addr = {"name": "Hans Dampf", "street1": "Holstenstr. 40", "city": "Luebeck", "postcode": "23552", "country_code": "DE", "phone_number": "844-212-0689"}
    res = await _server({"contact_email": "ops@example.com"}).call_tool("create_order", {"items": items, "shipping_address": addr, "shipping_option": "MAIL"})
    assert res.is_error is False
    assert res.structured_content["id"] == "1" and res.structured_content["status"] == "CREATED"
    treq = token.calls[0].request
    assert parse_qs(treq.content.decode()) == {"grant_type": ["client_credentials"]}
    assert treq.headers["Authorization"] == "Basic " + base64.b64encode(b"ck:csSECRET").decode()
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Bearer eyJ.acc"
    body = json.loads(req.content)
    assert body["line_items"] == items and body["shipping_address"] == addr and body["shipping_level"] == "MAIL" and body["contact_email"] == "ops@example.com"
    assert len(body["external_id"]) == 36


@pytest.mark.asyncio
@respx.mock
async def test_track_reads_line_item_statuses():
    respx.post(TOKEN_URL).mock(return_value=_tok())
    respx.get(f"{API}/print-jobs/42776/status/").mock(return_value=httpx.Response(200, json={
        "name": "SHIPPED", "message": "All line-items were shipped", "changed": "2024-04-10T09:28:34.870842Z",
        "line_item_statuses": [{"name": "SHIPPED", "messages": {"tracking_id": "3d4a_1", "tracking_urls": ["https://track.example/3d4a_1"], "carrier_name": "Carrier"}, "line_item_id": 57999}],
        "print_job_id": 42776}))
    ev = (await _server().call_tool("track", {"order_id": "42776"})).structured_content["events"]
    assert ev[0]["tracking_number"] == "3d4a_1" and ev[0]["tracking_url"] == "https://track.example/3d4a_1" and ev[0]["carrier"] == "Carrier"


@pytest.mark.asyncio
@respx.mock
async def test_refused_token_is_an_auth_error_without_secrets():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(401, json={"error": "unauthorized_client", "error_description": "Invalid client secret csSECRET"}))
    res = await _server().call_tool("get_order", {"id": "1"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "csSECRET" not in json.dumps(res.structured_content)
