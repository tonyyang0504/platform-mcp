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

SPEC = json.loads((ROOT / "catalog" / "ads" / "seznam_sklik.json").read_text(encoding="utf-8"))
B = "https://api.sklik.cz/v1"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"refresh_token": "sklik-refresh-secret"}, 50, "test")
    return build_server(SPEC, transport=t)


def _login():
    return respx.post(f"{B}/user/token").mock(return_value=httpx.Response(200, json={"access_token": "SKAT", "token_type": "Bearer", "expires_in": 3600}))


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "list_accounts", "list_campaigns", "get_report", "update_budget", "pause_resume"}


@pytest.mark.asyncio
@respx.mock
async def test_refresh_token_form_login_then_campaign_list():
    login = _login()
    route = respx.get(f"{B}/sklik/campaigns/").mock(return_value=httpx.Response(200, json={"items": [
        {"id": 123, "name": "Podzim", "status": "active", "type": "fulltext", "startDate": "2026-09-01", "endDate": None, "budget": {"id": 9, "dayBudget": 50000}}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "x", "status": "active", "limit": 10})
    assert res.is_error is False
    assert {k: v[0] for k, v in parse_qs(login.calls[0].request.content.decode()).items()} == {"grant_type": "refresh_token", "refresh_token": "sklik-refresh-secret"}
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Bearer SKAT"
    q = parse_qs(urlparse(str(req.url)).query)
    assert q["a"] == ["id", "name", "status", "type", "startDate", "endDate", "budget.id", "budget.dayBudget"]
    assert q["status"] == ["active"] and q["limit"] == ["10"] and q["offset"] == ["0"] and q["isDeleted"] == ["false"]
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["status"], c["budget"]) == ("123", "active", 50000)


@pytest.mark.asyncio
@respx.mock
async def test_get_report_daily_statistics():
    _login()
    route = respx.get(f"{B}/sklik/campaigns/").mock(return_value=httpx.Response(200, json={"items": [
        {"id": 123, "name": "Podzim", "firstDate": "2026-09-01", "impressions": 1000, "clicks": 25, "totalMoney": 31000, "conversions": 1}]}))
    res = await _server().call_tool("get_report", {"account_id": "x", "campaign_id": "123", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    q = parse_qs(urlparse(str(route.calls[0].request.url)).query)
    assert q["statisticsDateFrom"] == ["2026-09-01"] and q["statisticsDateTo"] == ["2026-09-07"] and q["statisticsGranularity"] == ["daily"] and q["id"] == ["123"]
    r = res.structured_content["rows"][0]
    assert (r["date"], r["clicks"], r["spend_hellers"]) == ("2026-09-01", 25, 31000)


@pytest.mark.asyncio
@respx.mock
async def test_patch_budget_and_pause_answer_204():
    _login()
    route = respx.patch(f"{B}/sklik/campaigns/123/").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("update_budget", {"campaign_id": "123", "daily_budget": 50000})
    assert res.is_error is False and res.structured_content["status"] == "updated"
    assert json.loads(route.calls[0].request.content) == {"budget": {"dayBudget": 50000}}
    res = await _server().call_tool("pause_resume", {"campaign_id": "123", "action": "pause"})
    assert json.loads(route.calls[1].request.content) == {"status": "suspend"}


@pytest.mark.asyncio
@respx.mock
async def test_refused_refresh_token_does_not_leak():
    respx.post(f"{B}/user/token").mock(return_value=httpx.Response(401, json={"detail": "invalid token sklik-refresh-secret"}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "sklik-refresh-secret" not in json.dumps(res.structured_content)
