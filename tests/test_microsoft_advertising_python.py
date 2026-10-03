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


SPEC = json.loads((ROOT / "catalog" / "ads" / "microsoft_advertising.json").read_text(encoding="utf-8"))
CM = "https://campaign.api.bingads.microsoft.com/CampaignManagement/v13"
CC = "https://clientcenter.api.bingads.microsoft.com/CustomerManagement/v13"
CREDS = {"client_id": "4c0b-app", "client_secret": "mssecret", "refresh_token": "M.R3_refresh", "developer_token": "BBD37VB98", "customer_id": "21025739", "account_id": "149082887"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], CREDS, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post("https://login.microsoftonline.com/common/oauth2/v2.0/token").mock(return_value=httpx.Response(200, json={"token_type": "Bearer", "scope": "https://ads.microsoft.com/msads.manage", "expires_in": 3599, "access_token": "EwB", "refresh_token": "M.R3_new"}))


@pytest.mark.asyncio
async def test_tools_follow_the_ads_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["list_accounts", "list_campaigns", "me", "pause_resume", "update_budget"]


@pytest.mark.asyncio
@respx.mock
async def test_token_with_scope_and_the_developer_customer_headers_on_rest_campaign_query():
    token = _token()
    route = respx.post(f"{CM}/Campaigns/QueryByAccountId").mock(return_value=httpx.Response(200, json={"Campaigns": [
        {"Id": "804002", "Name": "Brand search", "Status": "Active", "DailyBudget": 25.0, "BudgetType": "DailyBudgetStandard", "CampaignType": "Search", "TimeZone": "PacificTimeUSCanadaTijuana"}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "149082887"})
    assert res.is_error is False
    assert _form(token.calls[0].request) == {"grant_type": "refresh_token", "refresh_token": "M.R3_refresh", "scope": "https://ads.microsoft.com/msads.manage", "client_id": "4c0b-app", "client_secret": "mssecret"}
    h = route.calls[0].request.headers
    assert h["Authorization"] == "Bearer EwB" and h["DeveloperToken"] == "BBD37VB98" and h["CustomerId"] == "21025739" and h["CustomerAccountId"] == "149082887"
    assert json.loads(route.calls[0].request.content) == {"AccountId": "149082887"}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["name"], c["status"], c["budget"]) == ("804002", "Brand search", "Active", 25.0)


@pytest.mark.asyncio
@respx.mock
async def test_list_accounts_searches_the_configured_customer():
    _token()
    route = respx.post(f"{CC}/Accounts/Search").mock(return_value=httpx.Response(200, json={"Accounts": [{"Id": "149082887", "Name": "Acme US", "Number": "F119ABCD", "CurrencyCode": "USDollar", "AccountLifeCycleStatus": "Active"}]}))
    res = await _server().call_tool("list_accounts", {})
    assert res.is_error is False and res.structured_content["accounts"][0]["id"] == "149082887" and res.structured_content["accounts"][0]["currency"] == "USDollar"
    assert json.loads(route.calls[0].request.content) == {"Predicates": [{"Field": "CustomerId", "Operator": "Equals", "Value": "21025739"}], "PageInfo": {"Index": 0, "Size": 100}}


@pytest.mark.asyncio
@respx.mock
async def test_update_budget_puts_one_campaign_and_surfaces_partial_errors():
    _token()
    route = respx.put(f"{CM}/Campaigns").mock(return_value=httpx.Response(200, json={"PartialErrors": [{"Code": 1100, "ErrorCode": "CampaignServiceInvalidBudget", "Index": 0, "Message": "The budget is invalid."}]}))
    res = await _server().call_tool("update_budget", {"campaign_id": "804002", "daily_budget": 40})
    assert res.is_error is False and res.structured_content["partial_errors"][0]["ErrorCode"] == "CampaignServiceInvalidBudget"
    assert json.loads(route.calls[0].request.content) == {"AccountId": "149082887", "Campaigns": [{"Id": "804002", "DailyBudget": 40}]}


@pytest.mark.asyncio
@respx.mock
async def test_refused_refresh_is_an_auth_error_without_secrets():
    respx.post("https://login.microsoftonline.com/common/oauth2/v2.0/token").mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "error_description": "AADSTS70000: The provided value for the code parameter is not valid."}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    out = json.dumps(res.structured_content)
    assert "mssecret" not in out and "M.R3_refresh" not in out and "BBD37VB98" not in out


@pytest.mark.asyncio
@respx.mock
async def test_pause_resume_puts_the_mapped_status():
    _token()
    route = respx.put(f"{CM}/Campaigns").mock(return_value=httpx.Response(200, json={"PartialErrors": []}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "804002", "action": "pause"})
    assert res.is_error is False and res.structured_content["partial_errors"] == []
    assert json.loads(route.calls[0].request.content) == {"AccountId": "149082887", "Campaigns": [{"Id": "804002", "Status": "Paused"}]}
