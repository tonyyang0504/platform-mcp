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

SPEC = json.loads((ROOT / "catalog" / "ads" / "lazada_sponsored_solutions.json").read_text(encoding="utf-8"))
API = "https://api.lazada.sg/rest"
CREDS = {"app_key": "100001", "app_secret": "SECRET-laz", "refresh_token": "REFRESH-laz-1", "api_domain": "api.lazada.sg"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _tok():
    return respx.post(url__startswith="https://auth.lazada.com/rest/auth/token/refresh").mock(return_value=httpx.Response(200, json={
        "access_token": "ACCESS-laz", "refresh_token": "REFRESH-laz-2", "expires_in": 604800, "refresh_expires_in": 2592000, "code": "0", "country": "sg"}))


def _check_api_sign(req, api_name):
    p = dict(req.url.params)
    sig = p.pop("sign")
    assert sig == hmac.new(b"SECRET-laz", (api_name + "".join(k + v for k, v in sorted(p.items()))).encode(), hashlib.sha256).hexdigest().upper()
    return p


@pytest.mark.asyncio
@respx.mock
async def test_signed_refresh_then_signed_campaign_list(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_MCP_STATE_DIR", str(tmp_path))
    tok = _tok()
    cl = respx.get(url__startswith=f"{API}/sponsor/solutions/campaign/searchCampaignList").mock(return_value=httpx.Response(200, json={
        "code": "0", "success": "true", "totalCount": "1", "result": [{"campaignId": "101100024476086", "campaignName": "myCampaign", "dailyBudget": "25",
                                                                        "startDate": "2023-03-01", "endDate": "2023-05-01", "campaignSwitchStatus": "1"}]}))
    res = (await _server().call_tool("list_campaigns", {"account_id": "shop", "page": 1, "limit": 20})).structured_content
    c = res["campaigns"][0]
    assert c["id"] == "101100024476086" and c["name"] == "myCampaign" and c["status"] == "1" and c["start"] == "2023-03-01"
    t = tok.calls[0].request
    tq = dict(t.url.params)
    assert t.content == b"refresh_token=REFRESH-laz-1" and tq["app_key"] == "100001" and tq["sign_method"] == "sha256"
    payload = f"/auth/token/refreshapp_key100001refresh_tokenREFRESH-laz-1sign_methodsha256timestamp{tq['timestamp']}"
    assert tq["sign"] == hmac.new(b"SECRET-laz", payload.encode(), hashlib.sha256).hexdigest().upper()
    p = _check_api_sign(cl.calls[0].request, "/sponsor/solutions/campaign/searchCampaignList")
    assert p["access_token"] == "ACCESS-laz" and p["bizCode"] == "sponsoredSearch" and p["pageSize"] == "20" and p["app_key"] == "100001"
    assert json.loads((tmp_path / "lazada_sponsored_solutions.json").read_text())["refresh_token"] == "REFRESH-laz-2"


@pytest.mark.asyncio
@respx.mock
async def test_update_campaign_budget_and_switch():
    _tok()
    up = respx.post(url__startswith=f"{API}/sponsor/solutions/campaign/updateCampaign").mock(return_value=httpx.Response(200, json={"code": "0", "success": "true", "result": {}}))
    server = _server()
    assert (await server.call_tool("update_budget", {"campaign_id": "101100024476086", "daily_budget": 25.5})).structured_content["status"] == "updated"
    p = _check_api_sign(up.calls[0].request, "/sponsor/solutions/campaign/updateCampaign")
    assert p["campaignId"] == "101100024476086" and p["dayBudget"] == "25.5"
    assert (await server.call_tool("pause_resume", {"campaign_id": "101100024476086", "action": "pause"})).is_error is False
    assert _check_api_sign(up.calls[1].request, "/sponsor/solutions/campaign/updateCampaign")["switchStatus"] == "0"


@pytest.mark.asyncio
@respx.mock
async def test_report_rows_and_gateway_error():
    _tok()
    rp = respx.get(url__startswith=f"{API}/sponsor/solutions/report/getDiscoveryReportCampaign").mock(return_value=httpx.Response(200, json={
        "code": "0", "result": {"result": [{"campaignId": 1, "campaignName": "c", "impressions": 200, "clicks": 4, "spend": "1.50", "storeOrders": 1, "storeRevenue": "9.90"}]}}))
    server = _server()
    rep = (await server.call_tool("get_report", {"account_id": "shop", "date_from": "2026-09-01", "date_to": "2026-09-07"})).structured_content
    assert rep["rows"][0]["spend"] == "1.50" and rep["rows"][0]["campaign_id"] == "1"
    assert _check_api_sign(rp.calls[0].request, "/sponsor/solutions/report/getDiscoveryReportCampaign")["startDate"] == "2026-09-01"
    respx.get(url__startswith=f"{API}/sponsor/solutions/report/getDiscoveryReportCampaign").mock(return_value=httpx.Response(200, json={"type": "ISV", "code": "IllegalAccessToken", "message": "The specified access token is invalid"}))
    assert (await server.call_tool("get_report", {"account_id": "shop", "date_from": "2026-09-01", "date_to": "2026-09-07"})).is_error is True
