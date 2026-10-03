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

SPEC = json.loads((ROOT / "catalog" / "ads" / "kakao_moment.json").read_text(encoding="utf-8"))
A = "https://apis.moment.kakao.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"business_token": "KMOMTOKEN", "ad_account_id": "10000"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["get_report", "list_accounts", "list_campaigns", "me", "pause_resume", "update_budget"]


@pytest.mark.asyncio
@respx.mock
async def test_accounts_first_page_and_campaign_content():
    acc = respx.get(f"{A}/openapi/v4/adAccounts/pages").mock(return_value=httpx.Response(200, json={"content": [{"id": 111, "name": "테스트계정1", "memberType": "MASTER", "config": "ON"}], "totalElements": 92, "page": 0}))
    res = await _server().call_tool("list_accounts", {})
    assert dict(acc.calls[0].request.url.params) == {"page": "0", "size": "25"}
    assert res.structured_content["accounts"][0]["id"] == "111" and res.structured_content["total"] == 92
    camp = respx.get(f"{A}/openapi/v4/campaigns").mock(return_value=httpx.Response(200, json={"content": [{"id": 1111, "name": "캠페인 1", "config": "ON", "systemConfig": "ADMIN_STOP"}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "10000"})
    assert camp.calls[0].request.headers["adAccountId"] == "10000"
    assert res.structured_content["campaigns"][0]["status"] == "ON"


@pytest.mark.asyncio
@respx.mock
async def test_budget_and_status_put_bodies():
    b = respx.put(f"{A}/openapi/v4/campaigns/dailyBudgetAmount").mock(return_value=httpx.Response(200))
    s = respx.put(f"{A}/openapi/v4/campaigns/onOff").mock(return_value=httpx.Response(200))
    r1 = await _server().call_tool("update_budget", {"campaign_id": "5678", "daily_budget": 5000000})
    r2 = await _server().call_tool("pause_resume", {"campaign_id": "5678", "action": "resume"})
    assert json.loads(b.calls[0].request.content) == {"id": 5678, "dailyBudgetAmount": 5000000}
    assert json.loads(s.calls[0].request.content) == {"id": 5678, "config": "ON"}
    assert r1.structured_content["status"] == r2.structured_content["status"] == "updated"


@pytest.mark.asyncio
@respx.mock
async def test_report_query_and_rejected_budget_is_upstream_error_without_leak():
    rep = respx.get(f"{A}/openapi/v4/campaigns/report").mock(return_value=httpx.Response(200, json={"code": 200, "message": "Success", "data": [
        {"start": "2026-09-01", "end": "2026-09-01", "dimensions": {"campaign_id": "1234"}, "metrics": {"imp": 4, "click": 1, "ctr": 25.0, "cost": 150.0}}]}))
    res = await _server().call_tool("get_report", {"account_id": "10000", "campaign_id": "1234", "date_from": "20260901", "date_to": "20260902"})
    assert dict(rep.calls[0].request.url.params) == {"campaignId": "1234", "start": "20260901", "end": "20260902", "metricsGroup": "BASIC", "timeUnit": "DAY", "level": "CAMPAIGN"}
    assert res.structured_content["rows"][0]["spend"] == 150.0
    respx.put(f"{A}/openapi/v4/campaigns/dailyBudgetAmount").mock(return_value=httpx.Response(400, json={"code": -813, "msg": "KakaoMomentException", "extras": {"detailCode": 31011, "detailMsg": "min 50,000", "token": "KMOMTOKEN"}}))
    bad = await _server().call_tool("update_budget", {"campaign_id": "5678", "daily_budget": 100})
    assert bad.is_error is True and bad.structured_content["error"] == "upstream_error" and "KMOMTOKEN" not in json.dumps(bad.structured_content)
