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

SPEC = json.loads((ROOT / "catalog" / "ads" / "outbrain.json").read_text(encoding="utf-8"))
B = "https://api.outbrain.com/amplify/v0.1"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"ob_token": "ob-token-secret"}, 50, "test")
    return build_server(SPEC, transport=t)


def _q(req):
    return {k: v[0] for k, v in parse_qs(urlparse(str(req.url)).query).items()}


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "list_accounts", "list_campaigns", "get_report", "pause_resume"}


@pytest.mark.asyncio
@respx.mock
async def test_list_campaigns_pages_with_offset_and_token_header():
    route = respx.get(f"{B}/marketers/m1/campaigns").mock(return_value=httpx.Response(200, json={"count": 60, "campaigns": [
        {"id": "c1", "name": "Boost", "onAirReason": "RUNNING", "enabled": True, "currency": "USD", "budget": {"id": "b1", "amount": 100.0, "startDate": "2026-09-01"}}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "m1", "page": 2, "limit": 20})
    assert res.is_error is False
    assert route.calls[0].request.headers["OB-TOKEN-V1"] == "ob-token-secret"
    assert _q(route.calls[0].request) == {"limit": "20", "offset": "20"}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["status"], c["budget"], c["currency"], res.structured_content["total"]) == ("c1", "RUNNING", 100.0, "USD", 60)


@pytest.mark.asyncio
@respx.mock
async def test_get_report_daily_periodic_rows():
    route = respx.get(f"{B}/reports/marketers/m1/periodic").mock(return_value=httpx.Response(200, json={"totalResults": 1, "results": [
        {"metadata": {"id": "2026-09-01", "fromDate": "2026-09-01", "toDate": "2026-09-01"}, "metrics": {"impressions": 1000, "clicks": 9, "spend": 5.2, "ecpc": 0.58, "totalConversions": 1}}]}))
    res = await _server().call_tool("get_report", {"account_id": "m1", "campaign_id": "c1", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    assert _q(route.calls[0].request) == {"from": "2026-09-01", "to": "2026-09-07", "campaignId": "c1", "breakdown": "daily", "limit": "100"}
    r = res.structured_content["rows"][0]
    assert (r["date"], r["spend"], r["clicks"]) == ("2026-09-01", 5.2, 9)


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_and_expired_token():
    respx.get(f"{B}/marketers").mock(side_effect=[httpx.Response(429, headers={"Retry-After": "60"}), httpx.Response(401, text="token ob-token-secret expired")])
    res = await _server().call_tool("list_accounts", {})
    assert res.structured_content["error"] == "rate_limited"
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "ob-token-secret" not in json.dumps(res.structured_content)


@pytest.mark.asyncio
@respx.mock
async def test_pause_resume_sends_json_boolean_enabled():
    route = respx.put(f"{B}/campaigns/cmp9").mock(return_value=httpx.Response(200, json={"id": "cmp9", "enabled": False}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "cmp9", "action": "pause"})
    assert res.is_error is False and res.structured_content["status"] == "updated"
    assert json.loads(route.calls[0].request.content) == {"enabled": False}
    await _server().call_tool("pause_resume", {"campaign_id": "cmp9", "action": "resume"})
    assert json.loads(route.calls[1].request.content) == {"enabled": True}
