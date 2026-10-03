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


def _form(req):
    return {k: v[0] for k, v in parse_qs(req.content.decode()).items()}


async def _names(server):
    return sorted(t.name for t in await server.list_tools())

SPEC = json.loads((ROOT / "catalog" / "ads" / "revcontent.json").read_text(encoding="utf-8"))
A = "https://api.revcontent.io"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "rccid", "client_secret": "rcsecret40chars"}, 50, "test", envelope=SPEC["adapter"]["envelope"])
    return build_server(SPEC, transport=t)


def _token():
    return respx.post(f"{A}/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "20b9c0a27315af", "expires_in": 86400, "token_type": "Bearer", "scope": "advertiser"}))


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["get_report", "list_accounts", "list_campaigns", "me", "pause_resume", "update_budget"]


@pytest.mark.asyncio
@respx.mock
async def test_boosts_list_with_enabled_filter():
    token = _token()
    route = respx.get(f"{A}/stats/api/v1.0/boosts").mock(return_value=httpx.Response(200, json={"success": True, "data": [
        {"id": "218", "name": "Test Campaign 1", "enabled": "active", "status": "active", "budget": "295.00", "start_date": "2026-09-01 00:00:00", "end_date": None}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "me", "status": "active"})
    assert _form(token.calls[0].request)["client_secret"] == "rcsecret40chars"
    p = route.calls[0].request.url.params
    assert (p["enabled"], p["limit"], p["offset"]) == ("active", "25", "0")
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["budget"], c["currency"], c["status"]) == ("218", "295.00", "USD", "active")


@pytest.mark.asyncio
@respx.mock
async def test_budget_settings_and_status_bodies():
    _token()
    s = respx.post(f"{A}/stats/api/v1.0/boosts/218/settings").mock(return_value=httpx.Response(200, json={"id": "218", "budget": "80.00", "success": True}))
    st = respx.post(f"{A}/stats/api/v1.0/boosts").mock(return_value=httpx.Response(200, json={"id": "218", "enabled": "inactive", "status": "inactive"}))
    r1 = await _server().call_tool("update_budget", {"campaign_id": "218", "daily_budget": 80})
    r2 = await _server().call_tool("pause_resume", {"campaign_id": "218", "action": "pause"})
    assert json.loads(s.calls[0].request.content) == {"budget_type": "daily", "budget_amount": 80}
    assert json.loads(st.calls[0].request.content) == {"id": 218, "enabled": "off"}
    assert r1.structured_content["status"] == "updated" and r2.structured_content["status"] == "inactive"


@pytest.mark.asyncio
@respx.mock
async def test_success_false_envelope_is_an_error():
    _token()
    respx.get(f"{A}/stats/api/v1.0/boosts/performance").mock(return_value=httpx.Response(200, json={"success": False, "message": "Invalid date range"}))
    res = await _server().call_tool("get_report", {"account_id": "me", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is True and "Invalid date range" in res.structured_content["message"]
