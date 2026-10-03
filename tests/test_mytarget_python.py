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

SPEC = json.loads((ROOT / "catalog" / "ads" / "mytarget.json").read_text(encoding="utf-8"))
A = "https://ads.vk.ru"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "vkcid", "client_secret": "vksecret", "refresh_token": "vkrefresh"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post(f"{A}/api/v2/oauth2/token.json").mock(return_value=httpx.Response(200, json={"access_token": "VKTOKEN", "token_type": "bearer", "expires_in": "86400", "refresh_token": "vkrefresh"}))


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["get_report", "list_campaigns", "me", "pause_resume", "update_budget"]


@pytest.mark.asyncio
@respx.mock
async def test_refresh_grant_and_ad_plans_listing():
    token = _token()
    route = respx.get(f"{A}/api/v2/ad_plans.json").mock(return_value=httpx.Response(200, json={"count": 3, "offset": 0, "items": [
        {"id": 6617841, "name": "New campaign", "status": "active", "budget_limit_day": "1000", "budget_limit": "5000", "date_start": "2026-09-01"}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "me", "status": "active", "limit": 10, "page": 2})
    assert _form(token.calls[0].request) == {"grant_type": "refresh_token", "refresh_token": "vkrefresh", "client_id": "vkcid", "client_secret": "vksecret"}
    p = route.calls[0].request.url.params
    assert (p["limit"], p["offset"], p["_status"]) == ("10", "10", "active")
    assert route.calls[0].request.headers["Authorization"] == "Bearer VKTOKEN"
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["budget"], c["status"]) == ("6617841", "1000", "active") and res.structured_content["total"] == 3


@pytest.mark.asyncio
@respx.mock
async def test_budget_and_status_posts_to_the_ad_plan():
    _token()
    route = respx.post(f"{A}/api/v2/ad_plans/6617841.json").mock(return_value=httpx.Response(204))
    r1 = await _server().call_tool("update_budget", {"campaign_id": "6617841", "daily_budget": 1500.5})
    r2 = await _server().call_tool("pause_resume", {"campaign_id": "6617841", "action": "pause"})
    assert json.loads(route.calls[0].request.content) == {"budget_limit_day": "1500.5"}
    assert json.loads(route.calls[1].request.content) == {"status": "blocked"}
    assert r1.structured_content["status"] == r2.structured_content["status"] == "updated"


@pytest.mark.asyncio
@respx.mock
async def test_daily_statistics_rows_and_validation_error():
    _token()
    stat = respx.get(f"{A}/api/v2/statistics/ad_plans/day.json").mock(return_value=httpx.Response(200, json={"items": [{"id": 6617841, "rows": [
        {"date": "2026-09-01", "base": {"shows": 100, "clicks": 3, "spent": "12.50", "cpc": "4.1", "ctr": 3.0, "vk": {"goals": 1}}}], "total": {}}]}))
    res = await _server().call_tool("get_report", {"account_id": "me", "campaign_id": "6617841", "date_from": "2026-09-01", "date_to": "2026-09-02"})
    p = stat.calls[0].request.url.params
    assert (p["id"], p["date_from"], p["date_to"], p["metrics"]) == ("6617841", "2026-09-01", "2026-09-02", "base")
    r = res.structured_content["rows"][0]
    assert (r["date"], r["impressions"], r["spend"], r["goals"]) == ("2026-09-01", 100, "12.50", 1)
    respx.post(f"{A}/api/v2/ad_plans/1.json").mock(return_value=httpx.Response(400, json={"error": {"code": "validation_failed", "message": "Validation failed"}}))
    bad = await _server().call_tool("update_budget", {"campaign_id": "1", "daily_budget": -5})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input" and "vksecret" not in json.dumps(bad.structured_content)
