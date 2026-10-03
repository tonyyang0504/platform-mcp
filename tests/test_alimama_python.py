import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ads" / "alimama.json").read_text(encoding="utf-8"))
URL = "https://eco.taobao.com/router/rest"
CREDS = {"app_key": "12345678", "app_secret": "SECRET-top", "session": "SESSION-top", "biz_code": "onebpSearch"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _verify_sign(req):
    params = dict(req.url.params)
    sig = params.pop("sign")
    assert sig == hashlib.md5(("SECRET-top" + "".join(k + v for k, v in sorted(params.items())) + "SECRET-top").encode()).hexdigest().upper()
    return params


@pytest.mark.asyncio
@respx.mock
async def test_findpage_signed_with_gmt8_timestamp(monkeypatch):
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1790301600.0)
    route = respx.get(url__startswith=URL).mock(return_value=httpx.Response(200, json={
        "universalbp_new_campaign_findpage_response": {"top_result": {"info": {"ok": True}, "campaign_v_o_top_bulk_data": {"count": 1, "campaign_v_o_list": [
            {"campaign_id": 68796878069, "campaign_name": "管家计划", "display_status": "start", "day_budget": "100",
             "launch_time": {"start_time": "2023-06-09 00:00:00", "end_time": "2199-02-01 00:00:00"}}]}}}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "shop", "page": 2, "limit": 20})
    c = res.structured_content["campaigns"][0]
    assert c["id"] == "68796878069" and c["name"] == "管家计划" and c["status"] == "start" and c["start"] == "2023-06-09 00:00:00"
    p = _verify_sign(route.calls.last.request)
    assert p["timestamp"] == (datetime.fromtimestamp(1790301600, timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    assert p["method"] == "taobao.universalbp.new.campaign.findpage" and p["app_key"] == "12345678" and p["session"] == "SESSION-top"
    assert p["v"] == "2.0" and p["sign_method"] == "md5" and p["format"] == "json"
    assert json.loads(p["top_service_context"]) == {"biz_code": "onebpSearch"}
    assert json.loads(p["campaign_query_v_o"]) == {"offset": 20, "page_size": 20}


@pytest.mark.asyncio
@respx.mock
async def test_budget_and_pause_methods():
    route = respx.get(url__startswith=URL).mock(return_value=httpx.Response(200, json={"universalbp_new_campaign_budget_batchupdate_response": {"top_result": {"info": {"ok": True}}}}))
    assert (await _server().call_tool("update_budget", {"campaign_id": "68796878069", "daily_budget": 150})).structured_content["status"] == "updated"
    p = _verify_sign(route.calls.last.request)
    assert p["method"] == "taobao.universalbp.new.campaign.budget.batchupdate"
    assert json.loads(p["campaign_budget_list_v_o"]) == {"budget_list": [{"campaign_id": 68796878069, "dmc_type": "normal", "day_budget": 150}]}
    assert (await _server().call_tool("pause_resume", {"campaign_id": "68792788657", "action": "resume"})).is_error is False
    p = _verify_sign(route.calls.last.request)
    assert p["method"] == "taobao.universalbp.new.campaign.onerecover" and json.loads(p["one_click_v_o"]) == {"campaign_id_list": [68792788657]}


@pytest.mark.asyncio
@respx.mock
async def test_report_query_and_error_response():
    route = respx.get(url__startswith=URL).mock(return_value=httpx.Response(200, json={"universalbp_new_report_query_campaign_response": {"top_result": {
        "top_report_v_o_top_bulk_data": {"count": 1, "top_report_v_o_list": [{"thedate": "2026-09-01", "campaign_id": "1", "charge": "12.30", "click": "5"}]}}}}))
    rep = (await _server().call_tool("get_report", {"account_id": "shop", "date_from": "2026-09-01", "date_to": "2026-09-07"})).structured_content
    assert rep["rows"][0]["raw"]["charge"] == "12.30"
    q = json.loads(_verify_sign(route.calls.last.request)["top_campaign_report_query_v_o"])
    assert q["start_time"] == "2026-09-01" and q["end_time"] == "2026-09-07" and q["query_domains"] == ["date", "campaign"] and q["split_type"] == "day"
    respx.get(url__startswith=URL).mock(return_value=httpx.Response(200, json={"error_response": {"code": 50, "msg": "Remote service error", "sub_code": "isv.invalid-parameter", "sub_msg": "非法参数"}}))
    bad = await _server().call_tool("me", {})
    assert bad.is_error is True
