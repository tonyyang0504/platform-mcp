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

SPEC = json.loads((ROOT / "catalog" / "ads" / "google.json").read_text(encoding="utf-8"))
API = "https://googleads.googleapis.com/v25"
TOKEN_URL = "https://oauth2.googleapis.com/token"
CREDS = {"client_id": "cid.apps.googleusercontent.com", "client_secret": "gsecret-xyz", "refresh_token": "1//refresh-abc", "developer_token": "devtok123", "customer_id": "1234567890"}


def _server(**extra):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {**CREDS, **extra}, 50, "test")
    return build_server(SPEC, transport=t)


def _form(req):
    return {k: v[0] for k, v in parse_qs(req.content.decode()).items()}


@pytest.mark.asyncio
async def test_tools_are_the_documented_reads_only():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_report", "list_accounts", "list_campaigns", "me", "pause_resume"]
    assert set(SPEC["adapter"]["not_offered"]) == {"update_budget"}


@pytest.mark.asyncio
@respx.mock
async def test_refresh_grant_in_the_body_and_developer_and_login_customer_headers():
    token = respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "ya29.A1", "expires_in": 3599, "token_type": "Bearer"}))
    search = respx.post(f"{API}/customers/5550001111/googleAds:search").mock(return_value=httpx.Response(200, json={
        "results": [{"campaign": {"resourceName": "customers/5550001111/campaigns/42", "id": "42", "name": "Brand", "status": "ENABLED", "startDateTime": "2026-01-01 00:00:00", "endDateTime": "2037-12-30 23:59:59"},
                     "campaignBudget": {"resourceName": "customers/5550001111/campaignBudgets/7", "amountMicros": "50000000"}}],
        "fieldMask": "campaign.id,campaign.name,campaign.status,campaign.startDateTime,campaign.endDateTime,campaignBudget.amountMicros"}))
    res = await _server(login_customer_id="9998887777").call_tool("list_campaigns", {"account_id": "5550001111"})
    assert res.is_error is False
    assert _form(token.calls[0].request) == {"grant_type": "refresh_token", "refresh_token": "1//refresh-abc", "client_id": "cid.apps.googleusercontent.com", "client_secret": "gsecret-xyz"}
    assert "Authorization" not in token.calls[0].request.headers  # client_auth: body
    h = search.calls[0].request.headers
    assert h["Authorization"] == "Bearer ya29.A1" and h["developer-token"] == "devtok123" and h["login-customer-id"] == "9998887777"
    assert json.loads(search.calls[0].request.content)["query"].startswith("SELECT campaign.id, campaign.name, campaign.status")
    c = res.structured_content["campaigns"][0]
    assert c["id"] == "42" and c["name"] == "Brand" and c["status"] == "ENABLED" and c["start"] == "2026-01-01 00:00:00" and c["raw"]["campaignBudget"]["amountMicros"] == "50000000"


@pytest.mark.asyncio
@respx.mock
async def test_list_accounts_reads_the_customer_client_hierarchy_of_the_configured_customer():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "ya29.A1", "expires_in": 3599}))
    search = respx.post(f"{API}/customers/1234567890/googleAds:search").mock(return_value=httpx.Response(200, json={"results": [
        {"customerClient": {"resourceName": "customers/1234567890/customerClients/1234567890", "clientCustomer": "customers/1234567890", "level": "0", "manager": True, "descriptiveName": "MCC", "currencyCode": "USD", "timeZone": "America/New_York", "id": "1234567890"}},
        {"customerClient": {"resourceName": "customers/1234567890/customerClients/5550001111", "clientCustomer": "customers/5550001111", "level": "1", "manager": False, "descriptiveName": "Shop EU", "currencyCode": "EUR", "timeZone": "Europe/Berlin", "id": "5550001111"}}]}))
    res = await _server().call_tool("list_accounts", {})
    assert res.is_error is False
    assert [(a["id"], a["name"], a["currency"]) for a in res.structured_content["accounts"]] == [("1234567890", "MCC", "USD"), ("5550001111", "Shop EU", "EUR")]
    assert "FROM customer_client WHERE customer_client.level <= 1" in json.loads(search.calls[0].request.content)["query"]
    assert "login-customer-id" not in search.calls[0].request.headers  # optional config left unset


@pytest.mark.asyncio
@respx.mock
async def test_rejected_refresh_token_is_an_auth_error_without_the_secrets():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "error_description": "Token has been expired or revoked."}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    msg = json.dumps(res.structured_content)
    assert "gsecret-xyz" not in msg and "1//refresh-abc" not in msg and "devtok123" not in msg


@pytest.mark.asyncio
@respx.mock
async def test_pause_resume_mutates_the_composed_resource_name_with_a_status_mask():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "ya29.A1", "expires_in": 3599}))
    route = respx.post(f"{API}/customers/1234567890/campaigns:mutate").mock(return_value=httpx.Response(200, json={"results": [{"resourceName": "customers/1234567890/campaigns/42"}]}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "42", "action": "pause"})
    assert res.is_error is False and res.structured_content["status"] == "updated" and res.structured_content["resource_name"] == "customers/1234567890/campaigns/42"
    assert json.loads(route.calls[0].request.content) == {"operations": [{"update": {"resourceName": "customers/1234567890/campaigns/42", "status": "PAUSED"}, "updateMask": "status"}]}
    bad = await _server().call_tool("pause_resume", {"campaign_id": "42", "action": "delete"})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_get_report_puts_the_dates_into_the_gaql_between_clause():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "ya29.A1", "expires_in": 3599}))
    route = respx.post(f"{API}/customers/5550001111/googleAds:search").mock(return_value=httpx.Response(200, json={"results": [
        {"campaign": {"resourceName": "customers/5550001111/campaigns/42", "id": "42", "name": "Brand"}, "segments": {"date": "2026-09-01"},
         "metrics": {"impressions": "900", "clicks": "31", "costMicros": "12500000", "conversions": 2.0}}]}))
    res = await _server().call_tool("get_report", {"account_id": "5550001111", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    r = res.structured_content["rows"][0]
    assert (r["campaign_id"], r["date"], r["impressions"], r["clicks"], r["cost_micros"]) == ("42", "2026-09-01", "900", "31", "12500000")
    assert "WHERE segments.date BETWEEN '2026-09-01' AND '2026-09-07'" in json.loads(route.calls[0].request.content)["query"]
