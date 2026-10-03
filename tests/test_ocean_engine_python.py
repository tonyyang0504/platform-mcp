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

SPEC = json.loads((ROOT / "catalog" / "ads" / "ocean_engine.json").read_text(encoding="utf-8"))
API = "https://api.oceanengine.com/open_api"
CREDS = {"client_id": "1700000000", "client_secret": "SECRET-oe", "refresh_token": "REFRESH-oe-1", "advertiser_id": "4242"}


def _server(creds=None):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(creds or CREDS), 50, "test", envelope=a.get("envelope")))


def _mock_token():
    return respx.post(f"{API}/oauth2/refresh_token/").mock(return_value=httpx.Response(200, json={
        "code": 0, "message": "OK", "data": {"access_token": "ACCESS-oe", "refresh_token": "REFRESH-oe-2", "expires_in": 86400, "refresh_token_expires_in": 2592000}}))


@pytest.mark.asyncio
@respx.mock
async def test_refresh_uses_app_id_secret_and_rotates_nested_token(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_MCP_STATE_DIR", str(tmp_path))
    tok = _mock_token()
    me = respx.get(f"{API}/2/user/info/").mock(return_value=httpx.Response(200, json={"code": 0, "message": "OK", "data": {"display_name": "u", "id": 1}}))
    assert (await _server().call_tool("me", {})).is_error is False
    assert json.loads(tok.calls[0].request.content) == {"refresh_token": "REFRESH-oe-1", "app_id": "1700000000", "secret": "SECRET-oe"}
    assert me.calls[0].request.headers["Access-Token"] == "ACCESS-oe"
    assert "access_token" not in me.calls[0].request.url.params
    assert json.loads((tmp_path / "ocean_engine.json").read_text())["refresh_token"] == "REFRESH-oe-2"


@pytest.mark.asyncio
@respx.mock
async def test_accounts_take_the_minted_token_as_query_param_and_projects_filter():
    _mock_token()
    acc = respx.get(url__startswith=f"{API}/oauth2/advertiser/get/").mock(return_value=httpx.Response(200, json={
        "code": 0, "message": "OK", "data": {"list": [{"advertiser_id": 4242, "advertiser_name": "店铺A", "account_role": "ADVERTISER", "is_valid": True}]}}))
    server = _server()
    out = (await server.call_tool("list_accounts", {})).structured_content
    assert out["accounts"][0]["id"] == "4242" and out["accounts"][0]["name"] == "店铺A"
    assert acc.calls[0].request.url.params["access_token"] == "ACCESS-oe"
    pl = respx.get(url__startswith=f"{API}/v3.0/project/list/").mock(return_value=httpx.Response(200, json={
        "code": 0, "message": "OK", "data": {"list": [{"project_id": 77, "name": "项目1", "status_first": "PROJECT_STATUS_ENABLE"}], "page_info": {"page": 1, "page_size": 20, "total_number": 1}}}))
    res = (await server.call_tool("list_campaigns", {"account_id": "4242", "status": "PROJECT_STATUS_ENABLE"})).structured_content
    assert res["campaigns"][0]["id"] == "77" and res["total"] == 1
    q = pl.calls[0].request.url.params
    assert q["advertiser_id"] == "4242" and json.loads(q["filtering"]) == {"status_first": "PROJECT_STATUS_ENABLE"}
    assert "access_token" not in q and pl.calls[0].request.headers["Access-Token"] == "ACCESS-oe"


@pytest.mark.asyncio
@respx.mock
async def test_budget_status_and_report():
    _mock_token()
    b = respx.post(f"{API}/v3.0/project/budget/update/").mock(return_value=httpx.Response(200, json={"code": 0, "message": "OK", "data": {"project_ids": [77], "errors": []}}))
    s = respx.post(f"{API}/v3.0/project/status/update/").mock(return_value=httpx.Response(200, json={"code": 0, "message": "OK", "data": {"project_ids": [77]}}))
    server = _server()
    assert (await server.call_tool("update_budget", {"campaign_id": "77", "daily_budget": 300})).structured_content["status"] == "updated"
    assert json.loads(b.calls[0].request.content) == {"advertiser_id": 4242, "data": [{"project_id": 77, "budget_mode": "BUDGET_MODE_DAY", "budget": 300}]}
    assert (await server.call_tool("pause_resume", {"campaign_id": "77", "action": "pause"})).is_error is False
    assert json.loads(s.calls[0].request.content)["data"] == [{"project_id": 77, "opt_status": "DISABLE"}]
    r = respx.get(url__startswith=f"{API}/v3.0/report/custom/get/").mock(return_value=httpx.Response(200, json={
        "code": 0, "message": "OK", "data": {"rows": [{"dimensions": {"cdp_project_id": "77"}, "metrics": {"stat_cost": "12.00", "show_cnt": "100"}}], "page_info": {"total_number": 1}}}))
    rep = (await server.call_tool("get_report", {"account_id": "4242", "date_from": "2026-09-01", "date_to": "2026-09-07"})).structured_content
    assert rep["rows"][0]["raw"]["metrics"]["stat_cost"] == "12.00"
    q = r.calls[0].request.url.params
    assert q["start_time"] == "2026-09-01 00:00:00" and q["end_time"] == "2026-09-07 23:59:59" and json.loads(q["dimensions"]) == ["cdp_project_id"]


@pytest.mark.asyncio
@respx.mock
async def test_nonzero_code_is_error():
    _mock_token()
    respx.post(f"{API}/v3.0/project/status/update/").mock(return_value=httpx.Response(200, json={"code": 40002, "message": "No permission to operate account", "data": {}}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "77", "action": "resume"})
    assert res.is_error is True
