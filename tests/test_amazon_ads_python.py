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


SPEC = json.loads((ROOT / "catalog" / "ads" / "amazon_ads.json").read_text(encoding="utf-8"))
H = "https://advertising-api-eu.amazon.com"
CREDS = {"client_id": "amzn1.application-oa2-client.abc", "client_secret": "amzsecret", "refresh_token": "Atzr|refresh", "api_host": "advertising-api-eu.amazon.com", "profile_id": "3312345678901234"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], CREDS, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_everything_but_the_async_report_is_served():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["list_accounts", "list_campaigns", "me", "pause_resume", "update_budget"]
    assert set(SPEC["adapter"]["not_offered"]) == {"get_report"}


@pytest.mark.asyncio
@respx.mock
async def test_lwa_refresh_in_the_body_and_client_id_and_scope_headers_on_the_regional_host():
    token = respx.post("https://api.amazon.com/auth/o2/token").mock(return_value=httpx.Response(200, json={"access_token": "Atza|AT", "token_type": "bearer", "expires_in": 3600}))
    route = respx.get(f"{H}/v2/profiles").mock(return_value=httpx.Response(200, json=[
        {"profileId": 3312345678901234, "countryCode": "DE", "currencyCode": "EUR", "timezone": "Europe/Paris", "accountInfo": {"marketplaceStringId": "A1PA6795UKMFR9", "id": "A2XYZ", "type": "seller", "name": "Shop GmbH", "validPaymentMethod": True}}]))
    res = await _server().call_tool("list_accounts", {})
    assert res.is_error is False
    assert _form(token.calls[0].request) == {"grant_type": "refresh_token", "refresh_token": "Atzr|refresh", "client_id": "amzn1.application-oa2-client.abc", "client_secret": "amzsecret"}
    h = route.calls[0].request.headers
    assert h["Authorization"] == "Bearer Atza|AT" and h["Amazon-Advertising-API-ClientId"] == "amzn1.application-oa2-client.abc" and h["Amazon-Advertising-API-Scope"] == "3312345678901234"
    a = res.structured_content["accounts"][0]
    assert (a["id"], a["name"], a["currency"]) == ("3312345678901234", "Shop GmbH", "EUR")


@pytest.mark.asyncio
@respx.mock
async def test_me_reads_the_configured_profile():
    respx.post("https://api.amazon.com/auth/o2/token").mock(return_value=httpx.Response(200, json={"access_token": "Atza|AT", "expires_in": 3600}))
    respx.get(f"{H}/v2/profiles/3312345678901234").mock(return_value=httpx.Response(200, json={"profileId": 3312345678901234, "countryCode": "DE", "currencyCode": "EUR"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["ok"] is True and res.structured_content["account"]["currencyCode"] == "EUR"


@pytest.mark.asyncio
@respx.mock
async def test_forbidden_profile_is_an_auth_error_without_secrets():
    respx.post("https://api.amazon.com/auth/o2/token").mock(return_value=httpx.Response(200, json={"access_token": "Atza|AT", "expires_in": 3600}))
    respx.get(f"{H}/v2/profiles/3312345678901234").mock(return_value=httpx.Response(403, json={"code": "UNAUTHORIZED", "details": "Not authorized to access scope 3312345678901234"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "amzsecret" not in json.dumps(res.structured_content) and "Atzr|refresh" not in json.dumps(res.structured_content)


VND = "application/vnd.spCampaign.v3+json"


@pytest.mark.asyncio
@respx.mock
async def test_sp_campaign_list_sends_the_vendor_media_type_and_a_state_filter():
    respx.post("https://api.amazon.com/auth/o2/token").mock(return_value=httpx.Response(200, json={"access_token": "Atza|AT", "expires_in": 3600}))
    route = respx.post(f"{H}/sp/campaigns/list").mock(return_value=httpx.Response(200, headers={"Content-Type": VND}, json={"campaigns": [
        {"campaignId": "3001", "name": "SP auto", "state": "ENABLED", "targetingType": "AUTO", "budget": {"budget": 20.0, "budgetType": "DAILY"}, "startDate": "2026-01-01"}], "totalResults": 1}))
    res = await _server().call_tool("list_campaigns", {"account_id": "3312345678901234", "status": "ENABLED", "limit": 10})
    assert res.is_error is False
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["name"], c["status"], c["budget"], c["start"]) == ("3001", "SP auto", "ENABLED", 20.0, "2026-01-01") and res.structured_content["total"] == 1
    req = route.calls[0].request
    assert req.headers["Content-Type"] == VND and req.headers["Accept"] == VND and req.headers["Amazon-Advertising-API-Scope"] == "3312345678901234"
    assert json.loads(req.content) == {"maxResults": 10, "stateFilter": {"include": ["ENABLED"]}}


@pytest.mark.asyncio
@respx.mock
async def test_sp_update_budget_and_pause_read_the_207_multi_status():
    respx.post("https://api.amazon.com/auth/o2/token").mock(return_value=httpx.Response(200, json={"access_token": "Atza|AT", "expires_in": 3600}))
    route = respx.put(f"{H}/sp/campaigns").mock(side_effect=[
        httpx.Response(207, json={"campaigns": {"success": [{"campaignId": "3001", "index": 0, "campaign": {"campaignId": "3001", "state": "ENABLED", "budget": {"budget": 35.0, "budgetType": "DAILY"}}}], "error": []}}),
        httpx.Response(207, json={"campaigns": {"success": [{"campaignId": "3001", "index": 0, "campaign": {"campaignId": "3001", "state": "PAUSED"}}], "error": []}}),
        httpx.Response(207, json={"campaigns": {"success": [], "error": [{"index": 0, "errors": [{"errorType": "budgetError", "errorValue": {}}]}]}})])
    res = await _server().call_tool("update_budget", {"campaign_id": "3001", "daily_budget": 35})
    assert res.is_error is False and res.structured_content["status"] == "updated" and res.structured_content["campaign_id"] == "3001"
    assert route.calls[0].request.headers["Content-Type"] == VND
    assert json.loads(route.calls[0].request.content) == {"campaigns": [{"campaignId": "3001", "budget": {"budget": 35, "budgetType": "DAILY"}}]}
    res = await _server().call_tool("pause_resume", {"campaign_id": "3001", "action": "pause"})
    assert res.structured_content["status"] == "PAUSED" and json.loads(route.calls[1].request.content) == {"campaigns": [{"campaignId": "3001", "state": "PAUSED"}]}
    bad = await _server().call_tool("update_budget", {"campaign_id": "3001", "daily_budget": 0.5})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"
