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

SPEC = json.loads((ROOT / "catalog" / "ads" / "kuaishou_magnetic_engine.json").read_text(encoding="utf-8"))
API = "https://ad.e.kuaishou.com/rest/openapi"
CREDS = {"client_id": "74751", "client_secret": "SECRET-ks", "refresh_token": "REFRESH-ks-1", "advertiser_id": "20000800"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _tok():
    return respx.post(f"{API}/oauth2/authorize/refresh_token").mock(return_value=httpx.Response(200, json={
        "code": 0, "message": "OK", "data": {"access_token": "ACCESS-ks", "access_token_expires_in": 86400, "refresh_token": "REFRESH-ks-2", "refresh_token_expires_in": 2592000}}))


@pytest.mark.asyncio
@respx.mock
async def test_refresh_body_and_campaign_list(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_MCP_STATE_DIR", str(tmp_path))
    tok = _tok()
    cl = respx.post(f"{API}/gw/dsp/campaign/list").mock(return_value=httpx.Response(200, json={
        "code": 0, "message": "OK", "data": {"total_count": 1, "details": [{"campaign_id": 227785633, "campaign_name": "提高应用活跃", "put_status": 1, "status": 6, "day_budget": 0}]}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "20007185", "page": 1, "limit": 10})
    c = res.structured_content["campaigns"][0]
    assert c["id"] == "227785633" and c["name"] == "提高应用活跃" and res.structured_content["total"] == 1
    assert json.loads(tok.calls[0].request.content) == {"refresh_token": "REFRESH-ks-1", "app_id": "74751", "secret": "SECRET-ks"}
    req = cl.calls[0].request
    assert req.headers["Access-Token"] == "ACCESS-ks" and json.loads(req.content) == {"advertiser_id": 20007185, "page": 1, "page_size": 10}
    assert json.loads((tmp_path / "kuaishou_magnetic_engine.json").read_text())["refresh_token"] == "REFRESH-ks-2"


@pytest.mark.asyncio
@respx.mock
async def test_budget_in_li_and_status_codes():
    _tok()
    up = respx.post(f"{API}/gw/dsp/campaign/update").mock(return_value=httpx.Response(200, json={"code": 0, "message": "OK", "data": {"campaign_id": 2342843}}))
    st = respx.post(f"{API}/v1/campaign/update/status").mock(return_value=httpx.Response(200, json={"code": 0, "message": "OK", "data": {}}))
    server = _server()
    assert (await server.call_tool("update_budget", {"campaign_id": "2342843", "daily_budget": 888.5})).structured_content["status"] == "updated"
    assert json.loads(up.calls[0].request.content) == {"advertiser_id": 20000800, "campaign_id": 2342843, "day_budget": 888500}
    assert (await server.call_tool("pause_resume", {"campaign_id": "2960188", "action": "pause"})).is_error is False
    assert json.loads(st.calls[0].request.content) == {"advertiser_id": 20000800, "campaign_id": 2960188, "put_status": 2}


@pytest.mark.asyncio
@respx.mock
async def test_report_body_and_error_code():
    _tok()
    r = respx.post(f"{API}/v1/report/campaign_report").mock(return_value=httpx.Response(200, json={
        "code": 0, "message": "OK", "data": {"total_count": 1, "details": [{"stat_date": "2026-09-01", "campaign_id": 1, "charge": 12.5, "show": 100}]}}))
    server = _server()
    rep = (await server.call_tool("get_report", {"account_id": "486", "campaign_id": "1", "date_from": "2026-09-01", "date_to": "2026-09-07"})).structured_content
    assert rep["rows"][0]["raw"]["charge"] == 12.5
    assert json.loads(r.calls[0].request.content) == {"advertiser_id": 486, "start_date": "2026-09-01", "end_date": "2026-09-07", "campaign_ids": [1],
                                                      "temporal_granularity": "DAILY", "page": 1, "page_size": 2000}
    respx.post(f"{API}/v1/campaign/update/status").mock(return_value=httpx.Response(200, json={"code": 400002, "message": "参数错误", "data": {}}))
    assert (await server.call_tool("pause_resume", {"campaign_id": "1", "action": "resume"})).is_error is True
