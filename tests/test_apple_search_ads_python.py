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

SPEC = json.loads((ROOT / "catalog" / "ads" / "apple_search_ads.json").read_text(encoding="utf-8"))
A = "https://api.ads.apple.com"
JWT = "eyJhbGciOiJFUzI1NiJ9.clientsecretjwt.sig"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "SEARCHADS.abc", "client_secret": JWT, "ap_context": "adAccountId=123456789"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post("https://appleid.apple.com/auth/oauth2/token").mock(return_value=httpx.Response(200, json={"access_token": "APLTOKEN", "token_type": "Bearer", "expires_in": 3600, "scope": "searchadsorg"}))


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["get_report", "list_accounts", "list_campaigns", "me", "pause_resume", "update_budget"]


@pytest.mark.asyncio
@respx.mock
async def test_token_scope_context_header_and_campaign_query():
    token = _token()
    route = respx.post(f"{A}/v1/campaigns/query").mock(return_value=httpx.Response(200, json={"result": [
        {"id": 111222333, "name": "AwayFinder", "status": "ENABLED", "startTime": "2026-09-01T00:00:00.000", "dailyBudget": {"value": {"amount": "900.00", "currency": "USD"}}}],
        "pagination": {"totalCount": 3, "offset": 0, "pageSize": 25}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "123456789"})
    assert _form(token.calls[0].request) == {"grant_type": "client_credentials", "scope": "searchadsorg", "client_id": "SEARCHADS.abc", "client_secret": JWT}
    req = route.calls[0].request
    assert req.headers["X-AP-Context"] == "adAccountId=123456789" and req.headers["Authorization"] == "Bearer APLTOKEN"
    assert json.loads(req.content) == {"pagination": {"offset": 0, "pageSize": 25, "fetchTotalCount": True}}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["budget"], c["currency"]) == ("111222333", "900.00", "USD") and res.structured_content["total"] == 3


@pytest.mark.asyncio
@respx.mock
async def test_update_budget_sends_a_decimal_string_and_report_filters_by_campaign():
    _token()
    put = respx.put(f"{A}/v1/campaigns/111").mock(return_value=httpx.Response(200, json={"result": {"id": 111, "status": "ENABLED", "dailyBudget": {"value": {"amount": "1200.5", "currency": "USD"}}}}))
    res = await _server().call_tool("update_budget", {"campaign_id": "111", "daily_budget": 1200.5, "currency": "USD"})
    assert json.loads(put.calls[0].request.content) == {"dailyBudget": {"value": {"amount": "1200.5", "currency": "USD"}}}
    assert res.structured_content["status"] == "updated" and res.structured_content["campaign_id"] == "111"
    rep = respx.post(f"{A}/v1/reports/apps/campaigns/query").mock(return_value=httpx.Response(200, json={"result": {"rows": [
        {"metadata": {"id": 111, "name": "AwayFinder"}, "totalMetrics": {"impressions": 50000, "taps": 2500, "tapInstalls": 600, "localSpend": {"amount": "500.00", "currency": "USD"}}}]}}))
    r = await _server().call_tool("get_report", {"account_id": "123456789", "campaign_id": "111", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert json.loads(rep.calls[0].request.content) == {"filters": [{"field": "campaignId", "operator": "EQUALS", "value": "111"}], "timeRange": {"start": "2026-09-01", "end": "2026-09-07", "timeZone": "ORTZ"}}
    assert r.structured_content["rows"][0]["spend"] == "500.00"


@pytest.mark.asyncio
@respx.mock
async def test_expired_client_secret_is_auth_error_without_leak():
    respx.post("https://appleid.apple.com/auth/oauth2/token").mock(return_value=httpx.Response(400, json={"error": "invalid_client", "client_secret": JWT}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "111", "action": "pause"})
    assert res.structured_content["error"] == "auth_error" and JWT not in json.dumps(res.structured_content)
