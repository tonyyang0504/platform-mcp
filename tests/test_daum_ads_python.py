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

SPEC = json.loads((ROOT / "catalog" / "ads" / "daum_ads.json").read_text(encoding="utf-8"))
A = "https://api.keywordad.kakao.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"business_token": "KBIZTOKEN", "ad_account_id": "1111111111"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["get_report", "list_accounts", "list_campaigns", "me", "pause_resume", "update_budget"]


@pytest.mark.asyncio
@respx.mock
async def test_campaigns_carry_business_token_and_ad_account_header():
    route = respx.get(f"{A}/openapi/v1/campaigns").mock(return_value=httpx.Response(200, json=[
        {"bizChannelId": "2222222221", "id": "3333333331", "name": "캠페인1", "config": "ON", "status": ["LIVE"], "dailyBudgetAmount": 500000}]))
    res = await _server().call_tool("list_campaigns", {"account_id": "1111111111", "status": "ON"})
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Bearer KBIZTOKEN" and req.headers["adAccountId"] == "1111111111"
    assert dict(req.url.params) == {"config": "ON"}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["budget"], c["currency"], c["status"]) == ("3333333331", 500000, "KRW", "ON")


@pytest.mark.asyncio
@respx.mock
async def test_budget_is_a_whole_krw_amount_and_on_off_sends_id_and_config():
    budget = respx.patch(f"{A}/openapi/v1/campaigns/333/dailyBudget").mock(return_value=httpx.Response(200))
    onoff = respx.patch(f"{A}/openapi/v1/campaigns/333/onOff").mock(return_value=httpx.Response(200))
    res = await _server().call_tool("update_budget", {"campaign_id": "333", "daily_budget": 20000})
    assert res.is_error is False and res.structured_content["status"] == "updated"
    assert json.loads(budget.calls[0].request.content) == {"dailyBudgetAmount": 20000}
    bad = await _server().call_tool("update_budget", {"campaign_id": "333", "daily_budget": 199.5})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"
    await _server().call_tool("pause_resume", {"campaign_id": "333", "action": "pause"})
    assert json.loads(onoff.calls[0].request.content) == {"id": 333, "config": "OFF"}


@pytest.mark.asyncio
@respx.mock
async def test_report_rows_and_auth_error_without_token_leak():
    route = respx.get(f"{A}/openapi/v1/campaigns/report").mock(return_value=httpx.Response(200, json={"data": [
        {"start": "20260901", "end": "20260907", "dimensions": {"adAccountId": "1111111111", "campaignId": "3333333331"}, "metrics": {"imp": 105, "click": 10, "spending": 700.0, "ctr": 10.5}}]}))
    res = await _server().call_tool("get_report", {"account_id": "1111111111", "date_from": "20260901", "date_to": "20260907"})
    assert dict(route.calls[0].request.url.params) == {"start": "20260901", "end": "20260907", "metricsGroups": "BASIC"}
    r = res.structured_content["rows"][0]
    assert (r["campaign_id"], r["impressions"], r["spend"]) == ("3333333331", 105, 700.0)
    respx.get("https://kapi.kakao.com/v1/business/tokeninfo").mock(return_value=httpx.Response(401, json={"msg": "this access token does not exist KBIZTOKEN", "code": -401}))
    bad = await _server().call_tool("me", {})
    assert bad.structured_content["error"] == "auth_error" and "KBIZTOKEN" not in json.dumps(bad.structured_content)
