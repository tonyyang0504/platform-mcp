import hashlib
import hmac
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

SPEC = json.loads((ROOT / "catalog" / "ads" / "shopee_ads.json").read_text(encoding="utf-8"))
BASE = "https://partner.shopeemobile.com"
CREDS = {"partner_id": "1001", "shop_id": "2002", "partner_key": "PKEY-shopee-secret", "refresh_token": "REFRESH-sa-1"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _tok():
    return respx.post(url__startswith=f"{BASE}/api/v2/auth/access_token/get").mock(return_value=httpx.Response(200, json={
        "error": "", "message": "", "access_token": "ACCESS-sa", "refresh_token": "REFRESH-sa-2", "expire_in": 14400}))


def _sig(path, ts, token=""):
    return hmac.new(b"PKEY-shopee-secret", f"1001{path}{ts}{token}2002".encode() if token else f"1001{path}{ts}".encode(), hashlib.sha256).hexdigest()


@pytest.mark.asyncio
@respx.mock
async def test_signed_refresh_and_signed_balance_probe(monkeypatch):
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1790301600.0)
    tok = _tok()
    bal = respx.get(url__startswith=f"{BASE}/api/v2/ads/get_total_balance").mock(return_value=httpx.Response(200, json={
        "request_id": "r1", "error": "", "response": {"data_timestamp": 1689052069, "total_balance": 123.55}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["response"]["total_balance"] == 123.55
    t = tok.calls[0].request
    assert json.loads(t.content) == {"refresh_token": "REFRESH-sa-1", "partner_id": 1001, "shop_id": 2002}
    assert t.url.params["sign"] == hmac.new(b"PKEY-shopee-secret", b"1001/api/v2/auth/access_token/get1790301600", hashlib.sha256).hexdigest()
    q = bal.calls[0].request.url.params
    assert q["access_token"] == "ACCESS-sa" and q["partner_id"] == "1001" and q["shop_id"] == "2002" and q["timestamp"] == "1790301600"
    assert q["sign"] == _sig("/api/v2/ads/get_total_balance", 1790301600, "ACCESS-sa")


@pytest.mark.asyncio
@respx.mock
async def test_campaign_ids_and_daily_performance():
    _tok()
    cl = respx.get(url__startswith=f"{BASE}/api/v2/ads/get_product_level_campaign_id_list").mock(return_value=httpx.Response(200, json={
        "error": "", "response": {"shop_id": 2002, "region": "SG", "has_next_page": False, "campaign_list": [{"ad_type": "manual", "campaign_id": 1234}]}}))
    server = _server()
    res = (await server.call_tool("list_campaigns", {"account_id": "2002", "page": 2, "limit": 50})).structured_content
    assert res["campaigns"][0]["id"] == "1234" and res["campaigns"][0]["name"] == "manual"
    q = cl.calls[0].request.url.params
    assert q["offset"] == "50" and q["limit"] == "50" and q["ad_type"] == "all"
    pf = respx.get(url__startswith=f"{BASE}/api/v2/ads/get_all_cpc_ads_daily_performance").mock(return_value=httpx.Response(200, json={
        "error": "", "response": [{"date": "17-03-2021", "impression": 10, "clicks": 2, "expense": 1.23, "broad_order": 1, "broad_gmv": 9.9, "direct_roas": 2.1}]}))
    rep = (await server.call_tool("get_report", {"account_id": "2002", "date_from": "2021-03-17", "date_to": "2021-03-18"})).structured_content
    assert rep["rows"][0]["spend"] == 1.23 and rep["rows"][0]["clicks"] == 2
    q = pf.calls[0].request.url.params
    assert q["start_date"] == "17-03-2021" and q["end_date"] == "18-03-2021"


@pytest.mark.asyncio
@respx.mock
async def test_edit_actions_and_error_field():
    _tok()
    ed = respx.post(url__startswith=f"{BASE}/api/v2/ads/edit_manual_product_ads").mock(return_value=httpx.Response(200, json={"error": "", "message": "", "response": [{"campaign_id": 112234}]}))
    server = _server()
    assert (await server.call_tool("update_budget", {"campaign_id": "112234", "daily_budget": 10.5})).structured_content["status"] == "updated"
    b = json.loads(ed.calls[0].request.content)
    assert b["campaign_id"] == 112234 and b["edit_action"] == "change_budget" and b["budget"] == 10.5 and len(b["reference_id"]) == 36
    assert (await server.call_tool("pause_resume", {"campaign_id": "112234", "action": "pause"})).is_error is False
    assert json.loads(ed.calls[1].request.content)["edit_action"] == "pause"
    respx.post(url__startswith=f"{BASE}/api/v2/ads/edit_manual_product_ads").mock(return_value=httpx.Response(200, json={"error": "error_param", "message": "Wrong parameters."}))
    assert (await server.call_tool("pause_resume", {"campaign_id": "1", "action": "resume"})).is_error is True
