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

SPEC = json.loads((ROOT / "catalog" / "ads" / "snapchat.json").read_text(encoding="utf-8"))
A = "https://adsapi.snapchat.com/v1"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "snapcid", "client_secret": "snapsecret", "refresh_token": "snaprefresh1", "organization_id": "org1", "ad_account_id": "acc1", "tz_offset": "-07:00"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post("https://accounts.snapchat.com/login/oauth2/access_token").mock(return_value=httpx.Response(200, json={"access_token": "0.SNAPTOKEN", "expires_in": 3600, "refresh_token": "snaprefresh1"}))


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["get_report", "list_accounts", "list_campaigns", "me", "pause_resume"]


@pytest.mark.asyncio
@respx.mock
async def test_refresh_body_and_campaign_unwrap():
    token = _token()
    route = respx.get(f"{A}/adaccounts/acc1/campaigns").mock(return_value=httpx.Response(200, json={"request_status": "SUCCESS", "campaigns": [
        {"sub_request_status": "SUCCESS", "campaign": {"id": "c1", "name": "Badger", "status": "ACTIVE", "daily_budget_micro": 20000000, "start_time": "2026-09-01T00:00:00.000Z"}}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "acc1"})
    assert _form(token.calls[0].request) == {"grant_type": "refresh_token", "refresh_token": "snaprefresh1", "client_id": "snapcid", "client_secret": "snapsecret"}
    assert route.calls[0].request.url.params["limit"] == "50"
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["status"], c["budget_micros"]) == ("c1", "ACTIVE", 20000000)


@pytest.mark.asyncio
@respx.mock
async def test_day_stats_use_account_timezone_boundaries():
    _token()
    route = respx.get(f"{A}/campaigns/c1/stats").mock(return_value=httpx.Response(200, json={"request_status": "success", "timeseries_stats": [{"sub_request_status": "success", "timeseries_stat": {"id": "c1", "timeseries": [
        {"start_time": "2026-09-01T00:00:00.000-07:00", "end_time": "2026-09-02T00:00:00.000-07:00", "stats": {"impressions": 10, "swipes": 1, "spend": 2500000}}]}}]}))
    res = await _server().call_tool("get_report", {"account_id": "acc1", "campaign_id": "c1", "date_from": "2026-09-01", "date_to": "2026-09-02"})
    p = route.calls[0].request.url.params
    assert (p["start_time"], p["end_time"], p["granularity"]) == ("2026-09-01T00:00:00.000-07:00", "2026-09-02T00:00:00.000-07:00", "DAY")
    r = res.structured_content["rows"][0]
    assert (r["impressions"], r["spend_micros"]) == (10, 2500000)


@pytest.mark.asyncio
@respx.mock
async def test_json_patch_pause_and_expired_refresh_without_leak():
    _token()
    route = respx.patch(f"{A}/adaccounts/acc1/campaigns/c1").mock(return_value=httpx.Response(200, json={"request_status": "SUCCESS", "campaigns": [{"sub_request_status": "SUCCESS", "campaign": {"id": "c1", "status": "PAUSED"}}]}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "c1", "action": "pause"})
    req = route.calls[0].request
    assert req.headers["Content-Type"] == "application/json-patch+json"
    assert json.loads(req.content) == [{"op": "replace", "path": "/status", "value": "PAUSED"}]
    assert res.structured_content["status"] == "PAUSED"
    respx.post("https://accounts.snapchat.com/login/oauth2/access_token").mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "detail": "snaprefresh1"}))
    fresh = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "snapcid", "client_secret": "snapsecret", "refresh_token": "snaprefresh1"}, 50, "test")
    bad = await build_server(SPEC, transport=fresh).call_tool("me", {})
    assert bad.structured_content["error"] == "auth_error" and "snaprefresh1" not in json.dumps(bad.structured_content)
