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

SPEC = json.loads((ROOT / "catalog" / "ads" / "huawei_ads.json").read_text(encoding="utf-8"))
CREDS = {"client_id": "10380742", "client_secret": "SECRET-hw-1", "refresh_token": "REFRESH-hw-1"}
BASE = "https://ads.cloud.huawei.com"


def _server(creds=None):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(creds or CREDS), 50, "test", envelope=a.get("envelope")))


def _token():
    return respx.post("https://oauth-login.cloud.huawei.com/oauth2/v2/token").mock(return_value=httpx.Response(200, json={"access_token": "ACCESS-hw-1", "expires_in": 3600, "token_type": "Bearer"}))


@pytest.mark.asyncio
@respx.mock
async def test_refresh_grant_and_campaign_query_with_query_parameters():
    tok = _token()
    route = respx.get(url__startswith=BASE + "/openapi/v2/promotion/campaign/query").mock(return_value=httpx.Response(200, json={"code": "200", "data": {"total": 1, "data": [
        {"campaign_name": "美丽传说营销节", "campaign_id": "35002310", "show_status": "CAMPAIGN_STATUS_DELIVERY_OK", "campaign_status": "OPERATION_STATUS_ENABLE", "today_daily_budget": "40"}]}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "372155494770421376", "page": 2, "limit": 20})
    assert res.is_error is False
    c = res.structured_content["campaigns"][0]
    assert c["id"] == "35002310" and c["daily_budget"] == "40" and res.structured_content["total"] == 1
    form = parse_qs(tok.calls[0].request.content.decode())
    assert form == {"grant_type": ["refresh_token"], "refresh_token": ["REFRESH-hw-1"], "client_id": ["10380742"], "client_secret": ["SECRET-hw-1"]}
    req = route.calls[0].request
    assert req.method == "GET" and req.content == b""
    assert dict(req.url.params) == {"advertiser_id": "372155494770421376", "page_num": "2", "page_size": "20"}
    assert req.headers["Authorization"] == "Bearer ACCESS-hw-1"


@pytest.mark.asyncio
@respx.mock
async def test_numeric_200_on_edits_is_success_and_other_codes_fail():
    _token()
    route = respx.post(BASE + "/ads/v1/promotion/campaign/update").mock(side_effect=[
        httpx.Response(200, json={"code": 200}), httpx.Response(200, json={"code": 200}),
        httpx.Response(200, json={"code": "1000009992", "message": "token已过期"}), httpx.Response(200, json={"code": "200600", "message": "daily budget unchanged"})])
    s = _server({**CREDS, "advertiser_id": "425985380605536128"})
    r = await s.call_tool("update_budget", {"campaign_id": "30052950", "daily_budget": 500})
    assert r.is_error is False and r.structured_content["status"] == "updated"
    assert json.loads(route.calls[0].request.content) == {"advertiser_id": "425985380605536128", "campaign_id": "30052950", "daily_budget": {"daily_budget": 500, "daily_budget_op_type": "UPDATE_TODAY_DAILY_BUDGET"}}
    p = await s.call_tool("pause_resume", {"campaign_id": "30052950", "action": "pause"})
    assert p.is_error is False and json.loads(route.calls[1].request.content)["campaign_status"] == "OPERATION_DISABLE"
    e1 = await s.call_tool("pause_resume", {"campaign_id": "30052950", "action": "resume"})
    assert e1.is_error is True and e1.structured_content["error"] == "auth_error"
    e2 = await s.call_tool("update_budget", {"campaign_id": "30052950", "daily_budget": 500})
    assert e2.is_error is True and e2.structured_content["error"] == "upstream_error"


@pytest.mark.asyncio
@respx.mock
async def test_campaign_report_body_and_rows():
    _token()
    route = respx.post(BASE + "/openapi/v2/reports/campaign/query").mock(return_value=httpx.Response(200, json={"code": "200", "data": {
        "page_info": {"page": 1, "page_size": 1000, "total_num": 1, "total_page": 1},
        "list": [{"advertiser_id": "1", "campaign_id": "35002310", "campaign_name": "C", "stat_datetime": "2026090100", "show_count": 1000, "click_count": 20, "cost": "12.50", "cpc": "0.63"}]}}))
    res = await _server().call_tool("get_report", {"account_id": "425985380605536128", "campaign_id": "35002310", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    r = res.structured_content["rows"][0]
    assert r["spend"] == "12.50" and r["clicks"] == 20 and r["date"] == "2026090100"
    body = json.loads(route.calls[0].request.content)
    assert body["start_date"] == "2026-09-01" and body["end_date"] == "2026-09-07" and body["time_granularity"] == "STAT_TIME_GRANULARITY_DAILY"
    assert body["filtering"] == {"campaign_ids": ["35002310"]} and body["advertiser_id"] == "425985380605536128"


@pytest.mark.asyncio
@respx.mock
async def test_manager_advertiser_list():
    _token()
    respx.get(url__startswith=BASE + "/openapi/v2/manager/advertiser/query").mock(return_value=httpx.Response(200, json={"code": "200", "data": {"total": 2, "advertiser_info_list": [
        {"nick_name": "ces12", "advertiser_id": 427351382790547328}, {"nick_name": "", "advertiser_id": 372155494770421376}]}}))
    res = await _server().call_tool("list_accounts", {})
    assert [a["id"] for a in res.structured_content["accounts"]] == ["427351382790547328", "372155494770421376"]
