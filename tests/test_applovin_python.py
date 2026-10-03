import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ads" / "applovin.json").read_text(encoding="utf-8"))
M = "https://api.ads.axon.ai/manage/v1"


def _q(req):
    return {k: v[0] for k, v in parse_qs(urlparse(str(req.url)).query).items()}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"campaign_api_key": "cm-secret-key", "report_key": "rep-secret-key", "account_id": "777"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "list_campaigns", "get_report", "update_budget", "pause_resume"}


@pytest.mark.asyncio
@respx.mock
async def test_list_campaigns_pages_and_maps_global_budget():
    route = respx.get(f"{M}/campaign/list").mock(return_value=httpx.Response(200, json=[
        {"id": "12345", "name": "test campaign", "status": "LIVE", "budget": {"daily_budget_for_all_countries": "5000"}, "start_date": "2025-05-23T00:00:00", "end_date": "2025-05-30T00:00:00"}]))
    res = await _server().call_tool("list_campaigns", {"account_id": "777", "page": 2, "limit": 50})
    assert res.is_error is False
    req = route.calls[0].request
    assert req.headers["Authorization"] == "cm-secret-key"
    assert _q(req) == {"account_id": "777", "page": "2", "size": "50"}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["status"], c["budget"]) == ("12345", "LIVE", "5000")


@pytest.mark.asyncio
@respx.mock
async def test_get_report_uses_report_key_on_reporting_host():
    route = respx.get("https://r.applovin.com/report").mock(return_value=httpx.Response(200, json={"code": 200, "count": 1, "results": [
        {"day": "2026-09-01", "campaign": "UA US", "campaign_id_external": "abc", "impressions": "1000", "clicks": "20", "conversions": "3", "cost": "12.50"}]}))
    res = await _server().call_tool("get_report", {"account_id": "777", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    q = _q(route.calls[0].request)
    assert q["api_key"] == "rep-secret-key" and q["start"] == "2026-09-01" and q["end"] == "2026-09-07"
    assert q["report_type"] == "advertiser" and q["format"] == "json"
    assert res.structured_content["rows"][0]["spend"] == "12.50"


@pytest.mark.asyncio
@respx.mock
async def test_update_budget_and_pause_bodies():
    route = respx.post(f"{M}/campaign/update").mock(return_value=httpx.Response(200, json={"id": "12345"}))
    res = await _server().call_tool("update_budget", {"campaign_id": "12345", "daily_budget": 150.5})
    assert res.is_error is False and res.structured_content["status"] == "updated"
    assert _q(route.calls[0].request) == {"account_id": "777"}
    assert json.loads(route.calls[0].request.content) == {"id": "12345", "type": "APP", "budget": {"daily_budget_for_all_countries": "150.5"}}
    await _server().call_tool("pause_resume", {"campaign_id": "12345", "action": "pause"})
    assert json.loads(route.calls[1].request.content) == {"id": "12345", "type": "APP", "status": "PAUSED"}


@pytest.mark.asyncio
@respx.mock
async def test_refused_key_does_not_leak():
    respx.get(f"{M}/campaign/list").mock(return_value=httpx.Response(401, text="bad key cm-secret-key"))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "cm-secret-key" not in json.dumps(res.structured_content)
