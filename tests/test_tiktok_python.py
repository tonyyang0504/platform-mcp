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

SPEC = json.loads((ROOT / "catalog" / "ads" / "tiktok.json").read_text(encoding="utf-8"))
TT = "https://business-api.tiktok.com/open_api/v1.3"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"access_token": "act.tok", "app_id": "7001", "secret": "appsecret9", "advertiser_id": "6900"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_ads_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_report", "list_accounts", "list_campaigns", "me", "pause_resume", "update_budget"]


@pytest.mark.asyncio
@respx.mock
async def test_list_campaigns_sends_the_access_token_header_and_page_params():
    route = respx.get(f"{TT}/campaign/get/").mock(return_value=httpx.Response(200, json={"code": 0, "message": "OK", "request_id": "r1", "data": {
        "list": [{"advertiser_id": "6900", "campaign_id": "1800", "campaign_name": "Launch", "operation_status": "ENABLE", "secondary_status": "CAMPAIGN_STATUS_ENABLE", "budget_mode": "BUDGET_MODE_DAY", "budget": 50.0}],
        "page_info": {"page": 1, "page_size": 10, "total_number": 1, "total_page": 1}}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "6900", "limit": 10})
    assert res.is_error is False
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["name"], c["status"], c["budget"]) == ("1800", "Launch", "ENABLE", 50.0) and res.structured_content["total"] == 1
    req = route.calls[0].request
    assert req.headers["Access-Token"] == "act.tok" and "Authorization" not in req.headers
    assert dict(req.url.params) == {"advertiser_id": "6900", "page": "1", "page_size": "10"}


@pytest.mark.asyncio
@respx.mock
async def test_get_report_is_a_campaign_day_basic_report():
    route = respx.get(f"{TT}/report/integrated/get/").mock(return_value=httpx.Response(200, json={"code": 0, "message": "OK", "data": {
        "list": [{"dimensions": {"campaign_id": "1800", "stat_time_day": "2026-09-01 00:00:00"}, "metrics": {"spend": "12.50", "impressions": "900", "clicks": "31"}}],
        "page_info": {"page": 1, "page_size": 1000, "total_number": 1, "total_page": 1}}}))
    res = await _server().call_tool("get_report", {"account_id": "6900", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    r = res.structured_content["rows"][0]
    assert (r["campaign_id"], r["date"], r["spend"], r["impressions"], r["clicks"]) == ("1800", "2026-09-01 00:00:00", "12.50", "900", "31")
    p = route.calls[0].request.url.params
    assert p["report_type"] == "BASIC" and p["data_level"] == "AUCTION_CAMPAIGN" and json.loads(p["dimensions"]) == ["campaign_id", "stat_time_day"]
    assert p["start_date"] == "2026-09-01" and p["end_date"] == "2026-09-07" and p["advertiser_id"] == "6900"


@pytest.mark.asyncio
@respx.mock
async def test_update_budget_body_uses_the_configured_advertiser_and_code_errors_surface():
    route = respx.post(f"{TT}/campaign/update/").mock(side_effect=[
        httpx.Response(200, json={"code": 0, "message": "OK", "data": {"advertiser_id": "6900", "campaign_id": "1800", "budget": 80.0, "budget_mode": "BUDGET_MODE_DAY"}}),
        httpx.Response(200, json={"code": 40002, "message": "Budget below minimum", "data": {}})])
    res = await _server().call_tool("update_budget", {"campaign_id": "1800", "daily_budget": 80})
    assert res.is_error is False and res.structured_content["status"] == "updated" and res.structured_content["campaign_id"] == "1800"
    assert json.loads(route.calls[0].request.content) == {"advertiser_id": "6900", "campaign_id": "1800", "budget": 80}
    bad = await _server().call_tool("update_budget", {"campaign_id": "1800", "daily_budget": 1})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_list_accounts_passes_app_credentials_and_errors_do_not_leak_them():
    route = respx.get(f"{TT}/oauth2/advertiser/get/").mock(side_effect=[
        httpx.Response(200, json={"code": 0, "message": "OK", "data": {"list": [{"advertiser_id": "6900", "advertiser_name": "Shop"}]}}),
        httpx.Response(500, text="upstream failure secret=appsecret9")])
    res = await _server().call_tool("list_accounts", {})
    assert res.structured_content["accounts"][0]["id"] == "6900" and res.structured_content["accounts"][0]["name"] == "Shop"
    assert route.calls[0].request.url.params["app_id"] == "7001" and route.calls[0].request.url.params["secret"] == "appsecret9"
    bad = await _server().call_tool("me", {})
    assert bad.is_error is True and bad.structured_content["error"] == "upstream_error" and "appsecret9" not in json.dumps(bad.structured_content)


@pytest.mark.asyncio
@respx.mock
async def test_pause_resume_posts_a_one_element_campaign_ids_array_and_the_operation_status():
    route = respx.post(f"{TT}/campaign/status/update/").mock(return_value=httpx.Response(200, json={"code": 0, "message": "OK", "data": {"status": "DISABLE", "campaign_ids": ["1800"]}}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "1800", "action": "pause"})
    assert res.is_error is False and res.structured_content["status"] == "DISABLE"
    assert json.loads(route.calls[0].request.content) == {"advertiser_id": "6900", "campaign_ids": ["1800"], "operation_status": "DISABLE"}
