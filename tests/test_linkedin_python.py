import base64
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


def _form(req):
    return {k: v[0] for k, v in parse_qs(req.content.decode()).items()}


SPEC = json.loads((ROOT / "catalog" / "ads" / "linkedin.json").read_text(encoding="utf-8"))
L = "https://api.linkedin.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "86li", "client_secret": "lisecret", "refresh_token": "AQRrefresh", "ad_account_id": "506333826"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post("https://www.linkedin.com/oauth/v2/accessToken").mock(return_value=httpx.Response(200, json={"access_token": "AQVat", "expires_in": 5184000, "refresh_token": "AQRrefresh", "refresh_token_expires_in": 31536000}))


@pytest.mark.asyncio
async def test_tools_follow_the_ads_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_report", "list_accounts", "list_campaigns", "me", "pause_resume", "update_budget"]


@pytest.mark.asyncio
@respx.mock
async def test_refresh_grant_and_versioned_restli_headers_on_campaign_search():
    token = _token()
    route = respx.get(f"{L}/rest/adAccounts/506333826/adCampaigns").mock(return_value=httpx.Response(200, json={"elements": [
        {"id": 186000001, "name": "Q3 leads", "status": "ACTIVE", "account": "urn:li:sponsoredAccount:506333826", "dailyBudget": {"amount": "25", "currencyCode": "USD"}, "runSchedule": {"start": 1756684800000}}],
        "metadata": {"nextPageToken": None}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "506333826", "status": "ACTIVE", "limit": 10})
    assert res.is_error is False
    assert _form(token.calls[0].request) == {"grant_type": "refresh_token", "refresh_token": "AQRrefresh", "client_id": "86li", "client_secret": "lisecret"}
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Bearer AQVat" and req.headers["Linkedin-Version"] == "202609" and req.headers["X-Restli-Protocol-Version"] == "2.0.0"
    assert req.url.params["q"] == "search" and req.url.params["search.test"] == "false" and req.url.params["search.status.values[0]"] == "ACTIVE" and req.url.params["pageSize"] == "10"
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["name"], c["status"], c["currency"]) == ("186000001", "Q3 leads", "ACTIVE", "USD")


@pytest.mark.asyncio
@respx.mock
async def test_list_accounts_and_me_use_the_documented_finders():
    _token()
    accts = respx.get(f"{L}/rest/adAccounts").mock(return_value=httpx.Response(200, json={"elements": [{"id": 506333826, "name": "Acme", "currency": "USD", "status": "ACTIVE", "type": "BUSINESS"}], "metadata": {}}))
    users = respx.get(f"{L}/rest/adAccountUsers").mock(return_value=httpx.Response(200, json={"elements": [{"account": "urn:li:sponsoredAccount:506333826", "role": "ACCOUNT_MANAGER"}]}))
    res = await _server().call_tool("list_accounts", {})
    assert res.structured_content["accounts"][0]["id"] == "506333826" and res.structured_content["accounts"][0]["currency"] == "USD"
    assert accts.calls[0].request.url.params["q"] == "search"
    me = await _server().call_tool("me", {})
    assert me.is_error is False and users.calls[0].request.url.params["q"] == "authenticatedUser"


@pytest.mark.asyncio
@respx.mock
async def test_expired_refresh_token_is_an_auth_error_without_secrets():
    respx.post("https://www.linkedin.com/oauth/v2/accessToken").mock(return_value=httpx.Response(400, json={"error": "invalid_request", "error_description": "The provided authorization grant is invalid"}))
    res = await _server().call_tool("list_accounts", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "lisecret" not in json.dumps(res.structured_content) and "AQRrefresh" not in json.dumps(res.structured_content)


@pytest.mark.asyncio
@respx.mock
async def test_partial_updates_carry_the_restli_method_header_and_a_patch_set_body():
    _token()
    route = respx.post(f"{L}/rest/adAccounts/506333826/adCampaigns/186000001").mock(return_value=httpx.Response(204))
    res = await _server().call_tool("update_budget", {"campaign_id": "186000001", "daily_budget": 40, "currency": "USD"})
    assert res.is_error is False and res.structured_content["status"] == "updated"
    req = route.calls[0].request
    assert req.headers["X-RestLi-Method"] == "PARTIAL_UPDATE" and req.headers["Linkedin-Version"] == "202609"
    assert json.loads(req.content) == {"patch": {"$set": {"dailyBudget": {"amount": "40", "currencyCode": "USD"}}}}
    res = await _server().call_tool("pause_resume", {"campaign_id": "186000001", "action": "resume"})
    assert res.is_error is False and json.loads(route.calls[1].request.content) == {"patch": {"$set": {"status": "ACTIVE"}}}
    bad = await _server().call_tool("pause_resume", {"campaign_id": "186000001", "action": "stop"})
    assert bad.is_error is True


@pytest.mark.asyncio
@respx.mock
async def test_get_report_sends_a_literal_restli_date_range_and_account_urn_list():
    _token()
    route = respx.get(url__startswith=f"{L}/rest/adAnalytics").mock(return_value=httpx.Response(200, json={"elements": [
        {"pivotValues": ["urn:li:sponsoredCampaign:186000001"], "dateRange": {"start": {"year": 2026, "month": 9, "day": 1}, "end": {"year": 2026, "month": 9, "day": 1}},
         "impressions": 900, "clicks": 31, "costInLocalCurrency": "12.5"}]}))
    res = await _server().call_tool("get_report", {"account_id": "506333826", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    r = res.structured_content["rows"][0]
    assert (r["campaign"], r["year"], r["month"], r["day"], r["impressions"], r["spend"]) == ("urn:li:sponsoredCampaign:186000001", 2026, 9, 1, 900, "12.5")
    raw = str(route.calls[0].request.url)
    assert raw.startswith(f"{L}/rest/adAnalytics?q=analytics&pivot=CAMPAIGN&timeGranularity=DAILY&")
    assert "dateRange=(start:(year:2026,month:9,day:1),end:(year:2026,month:9,day:7))" in raw
    assert "accounts=List(urn%3Ali%3AsponsoredAccount%3A506333826)" in raw
    assert "fields=dateRange,pivotValues,impressions,clicks,costInLocalCurrency,externalWebsiteConversions" in raw
