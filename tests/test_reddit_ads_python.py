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

SPEC = json.loads((ROOT / "catalog" / "ads" / "reddit.json").read_text(encoding="utf-8"))
A = "https://ads-api.reddit.com/api/v3"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "rdcid", "client_secret": "rdsecret", "refresh_token": "rd-refresh-1", "business_id": "biz9"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post("https://www.reddit.com/api/v1/access_token").mock(return_value=httpx.Response(200, json={"access_token": "RDTOKEN1", "token_type": "bearer", "expires_in": 3600, "scope": "adsread adsedit"}))


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["get_report", "list_accounts", "list_campaigns", "me", "pause_resume"]


@pytest.mark.asyncio
@respx.mock
async def test_refresh_uses_basic_auth_and_accounts_come_from_business():
    token = _token()
    route = respx.get(f"{A}/businesses/biz9/ad_accounts").mock(return_value=httpx.Response(200, json={"data": [{"id": "t2_abc", "name": "Main", "currency": "USD", "time_zone_id": "America/New_York"}], "pagination": {}}))
    res = await _server().call_tool("list_accounts", {})
    treq = token.calls[0].request
    assert treq.headers["Authorization"].startswith("Basic ") and _form(treq) == {"grant_type": "refresh_token", "refresh_token": "rd-refresh-1"}
    assert route.calls[0].request.headers["Authorization"] == "Bearer RDTOKEN1"
    assert res.structured_content["accounts"][0] == {"id": "t2_abc", "name": "Main", "currency": "USD", "raw": {"id": "t2_abc", "name": "Main", "currency": "USD", "time_zone_id": "America/New_York"}}


@pytest.mark.asyncio
@respx.mock
async def test_report_body_uses_hourly_iso_bounds_and_breakdowns():
    _token()
    route = respx.post(f"{A}/ad_accounts/t2_abc/reports").mock(return_value=httpx.Response(200, json={"data": {"metrics": [
        {"campaign_id": "c1", "date": "2026-09-01", "impressions": 1000, "clicks": 12, "spend": 5230000, "ctr": 1.2, "cpc": 0.43}]}, "pagination": {}}))
    res = await _server().call_tool("get_report", {"account_id": "t2_abc", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert json.loads(route.calls[0].request.content) == {"data": {"starts_at": "2026-09-01T00:00:00Z", "ends_at": "2026-09-07T23:00:00Z", "breakdowns": ["CAMPAIGN_ID", "DATE"], "fields": ["IMPRESSIONS", "CLICKS", "SPEND", "CTR", "CPC"]}}
    r = res.structured_content["rows"][0]
    assert (r["campaign_id"], r["date"], r["spend_micros"]) == ("c1", "2026-09-01", 5230000)
    bad = await _server().call_tool("get_report", {"account_id": "t2_abc", "date_from": "09/01/2026", "date_to": "2026-09-07"})
    assert bad.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_pause_patch_and_forbidden_without_leak():
    _token()
    route = respx.patch(f"{A}/campaigns/c1").mock(side_effect=[
        httpx.Response(200, json={"data": {"id": "c1", "configured_status": "PAUSED", "effective_status": "PAUSED"}}),
        httpx.Response(403, json={"error": {"message": "forbidden for RDTOKEN1"}})])
    res = await _server().call_tool("pause_resume", {"campaign_id": "c1", "action": "pause"})
    assert json.loads(route.calls[0].request.content) == {"data": {"configured_status": "PAUSED"}}
    assert res.structured_content["status"] == "PAUSED"
    bad = await _server().call_tool("pause_resume", {"campaign_id": "c1", "action": "resume"})
    assert bad.structured_content["error"] == "auth_error" and "RDTOKEN1" not in json.dumps(bad.structured_content)
