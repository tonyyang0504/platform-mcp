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

SPEC = json.loads((ROOT / "catalog" / "ads" / "jd_jzt.json").read_text(encoding="utf-8"))
URL = "https://api.jd.com/routerjson"
CREDS = {"app_key": "APPKEY-jd", "app_secret": "SECRET-jd", "access_token": "TOKEN-jd"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _verify(req):
    p = dict(req.url.params)
    sig = p.pop("sign")
    assert sig == hashlib.md5(("SECRET-jd" + "".join(k + v for k, v in sorted(p.items())) + "SECRET-jd").encode()).hexdigest().upper()
    return p


@pytest.mark.asyncio
@respx.mock
async def test_campaign_list_signed_with_china_time(monkeypatch):
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1790301600.0)
    route = respx.get(url__startswith=URL).mock(return_value=httpx.Response(200, json={"jingdong_ads_dsp_rtb_kuaiche_campaign_list_v2_responce": {"data": {
        "msg": "成功", "code": "1", "success": True, "data": {"paginator": {"pageNum": 1, "pageSize": 20, "items": 1},
        "datas": [{"item": {"campaignId": "111", "campaignName": "test计划", "status": "2", "budget": "1000", "cost": "0.00"}}]}}}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "pin", "page": 1, "limit": 20})
    c = res.structured_content["campaigns"][0]
    assert c["id"] == "111" and c["name"] == "test计划" and c["status"] == "2" and res.structured_content["total"] == 1
    p = _verify(route.calls.last.request)
    assert p["timestamp"] == (datetime.fromtimestamp(1790301600, timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    assert p["method"] == "jingdong.ads.dsp.rtb.kuaiche.campaign.list.v2" and p["access_token"] == "TOKEN-jd" and p["v"] == "2.0"
    body = json.loads(p["360buy_param_json"])
    assert body["data"]["page"] == 1 and body["data"]["pageSize"] == 20 and len(body["data"]["startDay"]) == 10 and body["data"]["startDay"] == body["data"]["endDay"]
    assert body["system"] == {"platformBusinessType": "DST_JZT"}


@pytest.mark.asyncio
@respx.mock
async def test_budget_and_status_param_json():
    route = respx.get(url__startswith=URL).mock(return_value=httpx.Response(200, json={
        "jingdong_ads_dsp_rtb_kuaiche_campaign_updatebudget_v2_responce": {"data": {"msg": "成功", "code": "1", "success": True, "data": True}}}))
    out = (await _server().call_tool("update_budget", {"campaign_id": "111", "daily_budget": 300})).structured_content
    assert out["status"] == "updated" and out["success"] is True
    p = _verify(route.calls.last.request)
    assert p["method"] == "jingdong.ads.dsp.rtb.kuaiche.campaign.updatebudget.v2"
    assert json.loads(p["360buy_param_json"]) == {"data": {"id": 111, "dayBudget": 300}, "system": {"platformBusinessType": "DST_JZT"}}
    respx.get(url__startswith=URL).mock(return_value=httpx.Response(200, json={
        "jingdong_ads_dsp_rtb_kuaiche_campaign_updatestatus_v2_responce": {"data": {"code": "1", "success": True, "data": 1}}}))
    assert (await _server().call_tool("pause_resume", {"campaign_id": "111", "action": "pause"})).is_error is False
    p = _verify(respx.calls.last.request)
    assert json.loads(p["360buy_param_json"]) == {"data": {"ids": [111], "operateType": 1}, "system": {}}


@pytest.mark.asyncio
@respx.mock
async def test_gateway_error_response():
    respx.get(url__startswith=URL).mock(return_value=httpx.Response(200, json={"error_response": {"code": "19", "zh_desc": "access_token已过期", "en_desc": "Invalid access_token"}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True
