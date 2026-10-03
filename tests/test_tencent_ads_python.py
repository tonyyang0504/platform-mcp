import hashlib  # noqa: F401
import json
import re
import sys
import time
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ads" / "tencent_ads.json").read_text(encoding="utf-8"))
B = "https://api.e.qq.com/v3.0"


def _server():
    creds = {"client_id": "1110001", "client_secret": "SECRET-tq", "refresh_token": "REFRESH-tq", "account_id": "51959"}
    return build_server(SPEC, transport=Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds, 50, "test", envelope=SPEC["adapter"]["envelope"]))


def _token():
    return respx.get(url__startswith="https://api.e.qq.com/oauth/token").mock(return_value=httpx.Response(200, json={
        "code": 0, "message": "", "data": {"access_token": "ACCESS-tq", "access_token_expires_in": 86400, "refresh_token_expires_in": 2592000}}))


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "list_accounts", "list_campaigns", "get_report", "update_budget", "pause_resume"}


@pytest.mark.asyncio
@respx.mock
async def test_refresh_by_get_and_common_query_parameters():
    tok = _token()
    me = respx.get(url__startswith=f"{B}/advertiser/get").mock(return_value=httpx.Response(200, json={"code": 0, "message": "", "data": {"list": [{"account_id": 51959, "corporation_name": "腾讯"}]}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False
    tq = tok.calls[0].request.url.params
    assert (tq["grant_type"], tq["refresh_token"], tq["client_id"], tq["client_secret"]) == ("refresh_token", "REFRESH-tq", "1110001", "SECRET-tq")
    q = me.calls[0].request.url.params
    assert q["access_token"] == "ACCESS-tq" and q["account_id"] == "51959" and q["pagination_mode"] == "PAGINATION_MODE_NORMAL"
    assert abs(int(q["timestamp"]) - time.time()) < 60
    assert re.fullmatch(r"[0-9a-f]{32}", q["nonce"])
    assert json.loads(q["fields"])[0] == "account_id"


@pytest.mark.asyncio
@respx.mock
async def test_adgroups_list_and_nonce_is_fresh_per_call():
    _token()
    route = respx.get(url__startswith=f"{B}/adgroups/get").mock(return_value=httpx.Response(200, json={"code": 0, "message": "", "data": {
        "list": [{"adgroup_id": 7001, "adgroup_name": "春季", "configured_status": "AD_STATUS_NORMAL", "daily_budget": 50000, "begin_date": "2026-09-01", "end_date": "2026-12-31"}],
        "page_info": {"page": 1, "page_size": 25, "total_number": 1, "total_page": 1}}}))
    s = _server()
    res = await s.call_tool("list_campaigns", {"account_id": "51959"})
    await s.call_tool("list_campaigns", {"account_id": "51959", "page": 2})
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["name"], c["status"], c["raw"]["daily_budget"]) == ("7001", "春季", "AD_STATUS_NORMAL", 50000)
    q1, q2 = route.calls[0].request.url.params, route.calls[1].request.url.params
    assert q1["page_size"] == "25" and q2["page"] == "2" and q1["nonce"] != q2["nonce"]


@pytest.mark.asyncio
@respx.mock
async def test_daily_report_json_query_values():
    _token()
    route = respx.get(url__startswith=f"{B}/daily_reports/get").mock(return_value=httpx.Response(200, json={"code": 0, "message": "", "data": {
        "list": [{"date": "2026-09-01", "adgroup_id": 7001, "view_count": 1000, "valid_click_count": 20, "cost": 12345, "conversions_count": 2}]}}))
    res = await _server().call_tool("get_report", {"account_id": "51959", "campaign_id": "7001", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False and res.structured_content["rows"][0]["cost_fen"] == 12345
    q = route.calls[0].request.url.params
    assert json.loads(q["date_range"]) == {"start_date": "2026-09-01", "end_date": "2026-09-07"}
    assert json.loads(q["filtering"]) == [{"field": "adgroup_id", "operator": "EQUALS", "values": ["7001"]}]
    assert q["level"] == "REPORT_LEVEL_ADGROUP" and json.loads(q["group_by"]) == ["date", "adgroup_id"]


@pytest.mark.asyncio
@respx.mock
async def test_budget_in_fen_status_and_code_envelope():
    _token()
    route = respx.post(url__startswith=f"{B}/adgroups/update").mock(side_effect=[
        httpx.Response(200, json={"code": 0, "message": "", "data": {"adgroup_id": 7001}}),
        httpx.Response(200, json={"code": 0, "message": "", "data": {"adgroup_id": 7001}}),
        httpx.Response(200, json={"code": 31001, "message": "daily budget too low", "data": {}})])
    s = _server()
    res = await s.call_tool("update_budget", {"campaign_id": "7001", "daily_budget": 123.45})
    assert res.is_error is False and res.structured_content["status"] == "updated"
    assert json.loads(route.calls[0].request.content) == {"account_id": 51959, "adgroup_id": 7001, "daily_budget": 12345}
    await s.call_tool("pause_resume", {"campaign_id": "7001", "action": "pause"})
    assert json.loads(route.calls[1].request.content)["configured_status"] == "AD_STATUS_SUSPEND"
    bad = await s.call_tool("update_budget", {"campaign_id": "7001", "daily_budget": 1})
    assert bad.is_error is True and "ACCESS-tq" not in json.dumps(bad.structured_content)
