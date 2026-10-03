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

SPEC = json.loads((ROOT / "catalog" / "ads" / "xiaohongshu_pugongying.json").read_text(encoding="utf-8"))
API = "https://adapi.xiaohongshu.com/api/open"
CREDS = {"client_id": "1", "client_secret": "SECRET-xhs", "refresh_token": "REFRESH-xhs-1", "advertiser_id": "1234"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _tok():
    return respx.post(f"{API}/oauth2/refresh_token").mock(return_value=httpx.Response(200, json={"code": 0, "success": True, "msg": "成功", "data": {
        "access_token": "ACCESS-xhs", "access_token_expires_in": 86399, "refresh_token": "REFRESH-xhs-2", "refresh_token_expires_in": 2591999,
        "approval_advertisers": [{"advertiser_id": 1234, "advertiser_name": "品牌测试账号"}]}}))


@pytest.mark.asyncio
@respx.mock
async def test_refresh_rotation_and_campaign_list(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_MCP_STATE_DIR", str(tmp_path))
    tok = _tok()
    cl = respx.post(f"{API}/jg/campaign/list").mock(return_value=httpx.Response(200, json={"code": 0, "success": True, "msg": "成功", "data": {
        "page": {"page_index": 1, "total_count": 1}, "base_campaign_dtos": [{"campaign_id": 9876, "campaign_name": "产品种草_计划", "campaign_filter_state": 1,
                                                                         "campaign_day_budget": 10000, "start_time": "2023-10-20", "expire_time": "2023-11-20"}]}}))
    res = (await _server().call_tool("list_campaigns", {"account_id": "1234", "page": 1, "limit": 20})).structured_content
    assert res["campaigns"][0]["id"] == "9876" and res["campaigns"][0]["name"] == "产品种草_计划" and res["total"] == 1
    assert json.loads(tok.calls[0].request.content) == {"refresh_token": "REFRESH-xhs-1", "app_id": "1", "secret": "SECRET-xhs"}
    req = cl.calls[0].request
    assert req.headers["Access-Token"] == "ACCESS-xhs" and json.loads(req.content) == {"advertiser_id": 1234, "page": {"page_index": 1, "page_size": 20}}
    assert json.loads((tmp_path / "xiaohongshu_pugongying.json").read_text())["refresh_token"] == "REFRESH-xhs-2"


@pytest.mark.asyncio
@respx.mock
async def test_budget_in_fen_and_status_action():
    _tok()
    up = respx.post(f"{API}/jg/campaign/update").mock(return_value=httpx.Response(200, json={"code": 0, "success": True, "data": {"campaign_id": 9876}}))
    st = respx.post(f"{API}/jg/campaign/status/update").mock(return_value=httpx.Response(200, json={"code": 0, "success": True, "data": {"campaign_ids": [9876]}}))
    server = _server()
    assert (await server.call_tool("update_budget", {"campaign_id": "9876", "daily_budget": 150})).structured_content["status"] == "updated"
    assert json.loads(up.calls[0].request.content) == {"advertiser_id": 1234, "campaign_id": 9876, "limit_day_budget": 1, "campaign_day_budget": 15000}
    assert (await server.call_tool("pause_resume", {"campaign_id": "9876", "action": "pause"})).is_error is False
    assert json.loads(st.calls[0].request.content) == {"advertiser_id": 1234, "campaign_ids": [9876], "action_type": 2}


@pytest.mark.asyncio
@respx.mock
async def test_offline_report_and_error():
    _tok()
    rp = respx.post(f"{API}/jg/data/report/offline/campaign").mock(return_value=httpx.Response(200, json={"code": 0, "success": True, "data": {
        "data_list": [{"time": "2026-09-01", "campaign_id": "9876", "campaign_name": "c", "fee": "12.50", "impression": "100", "click": "7"}], "aggregation_data": {}}}))
    server = _server()
    rep = (await server.call_tool("get_report", {"account_id": "1234", "date_from": "2026-09-01", "date_to": "2026-09-07"})).structured_content
    assert rep["rows"][0]["spend"] == "12.50" and rep["rows"][0]["date"] == "2026-09-01"
    assert json.loads(rp.calls[0].request.content) == {"advertiser_id": 1234, "start_date": "2026-09-01", "end_date": "2026-09-07", "time_unit": "DAY", "page_num": 1, "page_size": 500}
    respx.post(f"{API}/jg/campaign/status/update").mock(return_value=httpx.Response(200, json={"code": 10001, "success": False, "msg": "参数错误"}))
    assert (await server.call_tool("pause_resume", {"campaign_id": "1", "action": "resume"})).is_error is True
