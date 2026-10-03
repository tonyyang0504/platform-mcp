import json
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ads" / "baidu_marketing.json").read_text(encoding="utf-8"))
CREDS = {"client_id": "APPID-bd-1", "client_secret": "SECRET-bd-1", "refresh_token": "REFRESH-bd-1", "user_id": "630152", "user_name": "shop-sem"}
API = "https://api.baidu.com/json/sms/service"
OK_HEADER = {"status": 0, "desc": "success", "failures": [], "oprs": 1, "quota": 1}


def _server(creds=None):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(creds or CREDS), 50, "test", envelope=a.get("envelope")))


def _token():
    return respx.post("https://u.baidu.com/oauth/refreshToken").mock(return_value=httpx.Response(200, json={
        "code": 0, "message": "success", "data": {"accessToken": "ACCESS-bd-1", "refreshToken": "REFRESH-bd-2", "expiresIn": 86400, "refreshExpiresIn": 2592000}}))


@pytest.mark.asyncio
@respx.mock
async def test_refresh_grant_fields_and_token_in_the_body_header():
    tok = _token()
    acct = respx.post(API + "/AccountService/getAccountInfo").mock(return_value=httpx.Response(200, json={"header": OK_HEADER, "body": {"data": [{"userId": 630152, "balance": 1200.5}]}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["body"]["data"][0]["userId"] == 630152
    assert json.loads(tok.calls[0].request.content) == {"refreshToken": "REFRESH-bd-1", "appId": "APPID-bd-1", "secretKey": "SECRET-bd-1", "userId": 630152}
    req = acct.calls[0].request
    body = json.loads(req.content)
    assert body["header"] == {"userName": "shop-sem", "accessToken": "ACCESS-bd-1"}
    assert "userId" in body["body"]["accountFields"] and "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_campaigns_for_an_account_name():
    _token()
    route = respx.post(API + "/CampaignService/getCampaign").mock(return_value=httpx.Response(200, json={"header": OK_HEADER, "body": {"data": [
        {"campaignId": 86415412, "campaignName": "测试计划", "budget": 50.0, "pause": False, "status": 21, "adType": 0}]}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "sub-account-2"})
    c = res.structured_content["campaigns"][0]
    assert c["id"] == "86415412" and c["name"] == "测试计划" and c["paused"] is False and c["budget"] == 50.0
    body = json.loads(route.calls[0].request.content)
    assert body["header"]["userName"] == "sub-account-2" and "campaignIds" not in body["body"]


@pytest.mark.asyncio
@respx.mock
async def test_campaign_report_rows():
    _token()
    route = respx.post(API + "/OpenApiReportService/getReportData").mock(return_value=httpx.Response(200, json={"header": OK_HEADER, "body": {"data": {
        "rows": [{"date": "2026-09-01", "campaignId": "922109731", "campaignName": "YD", "impression": "7334", "click": "221", "cost": "2294.99", "cpc": "10.38", "ctr": "3.01", "conversion": "0"}],
        "rowCount": 1, "totalRowCount": 1}}}))
    res = await _server().call_tool("get_report", {"account_id": "shop-sem", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    r = res.structured_content["rows"][0]
    assert r["spend"] == "2294.99" and r["clicks"] == "221" and r["campaign_id"] == "922109731"
    b = json.loads(route.calls[0].request.content)["body"]
    assert b["reportType"] == 2290316 and b["startDate"] == "2026-09-01" and b["endDate"] == "2026-09-07" and b["timeUnit"] == "DAY"


@pytest.mark.asyncio
@respx.mock
async def test_budget_and_pause_use_update_campaign():
    _token()
    route = respx.post(API + "/CampaignService/updateCampaign").mock(side_effect=[
        httpx.Response(200, json={"header": OK_HEADER, "body": {"data": [{"campaignId": 86415412, "budget": 300.0}]}}),
        httpx.Response(200, json={"header": OK_HEADER, "body": {"data": [{"campaignId": 86415412, "pause": True}]}}),
        httpx.Response(200, json={"header": {"status": 2, "desc": "failure", "failures": [{"code": 901, "message": "budget too low"}]}, "body": {"data": []}})])
    s = _server()
    r = await s.call_tool("update_budget", {"campaign_id": "86415412", "daily_budget": 300})
    assert r.structured_content["status"] == "updated"
    assert json.loads(route.calls[0].request.content)["body"] == {"campaignTypes": [{"campaignId": 86415412, "budget": 300}]}
    p = await s.call_tool("pause_resume", {"campaign_id": "86415412", "action": "pause"})
    assert p.structured_content["paused"] is True
    assert json.loads(route.calls[1].request.content)["body"]["campaignTypes"][0]["pause"] is True
    bad = await s.call_tool("update_budget", {"campaign_id": "86415412", "daily_budget": 1})
    assert bad.is_error is True
