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

SPEC = json.loads((ROOT / "catalog" / "ads" / "the_trade_desk.json").read_text(encoding="utf-8"))
A = "https://api.thetradedesk.com/v3"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_token": "ttd-tok-123", "partner_id": "p4rtn3r"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list():
    assert sorted(t.name for t in await _server().list_tools()) == ["list_accounts", "list_campaigns", "me", "update_budget"]


@pytest.mark.asyncio
@respx.mock
async def test_probe_and_advertisers_use_ttd_auth_and_partner_config():
    probe = respx.post(f"{A}/partner/query").mock(return_value=httpx.Response(200, json={"Result": [{"PartnerId": "p4rtn3r", "PartnerName": "Acme"}], "ResultCount": 1}))
    adv = respx.post(f"{A}/advertiser/query/partner").mock(return_value=httpx.Response(200, json={"Result": [{"AdvertiserId": "adv1", "AdvertiserName": "Brand", "CurrencyCode": "USD", "PartnerId": "p4rtn3r"}], "ResultCount": 1, "TotalFilteredCount": 1}))
    me = await _server().call_tool("me", {})
    assert me.structured_content["ok"] is True and probe.calls[0].request.headers["TTD-Auth"] == "ttd-tok-123"
    assert json.loads(probe.calls[0].request.content) == {"PageStartIndex": 0, "PageSize": 1}
    res = await _server().call_tool("list_accounts", {})
    assert json.loads(adv.calls[0].request.content) == {"PartnerId": "p4rtn3r", "PageStartIndex": 0, "PageSize": 100}
    a = res.structured_content["accounts"][0]
    assert (a["id"], a["name"], a["currency"], res.structured_content["total"]) == ("adv1", "Brand", "USD", 1)


@pytest.mark.asyncio
@respx.mock
async def test_campaign_query_pages_by_offset_and_filters_availability():
    route = respx.post(f"{A}/campaign/query/advertiser").mock(return_value=httpx.Response(200, json={"Result": [
        {"CampaignId": "c9", "CampaignName": "Fall", "Availability": "Available", "Budget": {"Amount": 5000.0, "CurrencyCode": "USD"}, "StartDate": "2026-09-01T00:00:00", "EndDate": None}],
        "ResultCount": 1, "TotalFilteredCount": 31}))
    res = await _server().call_tool("list_campaigns", {"account_id": "adv1", "status": "Available", "page": 2, "limit": 10})
    assert json.loads(route.calls[0].request.content) == {"AdvertiserId": "adv1", "PageStartIndex": 10, "PageSize": 10, "Availabilities": ["Available"]}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["status"], c["budget"], c["currency"]) == ("c9", "Available", 5000.0, "USD")
    assert res.structured_content["total"] == 31


@pytest.mark.asyncio
@respx.mock
async def test_update_budget_puts_daily_budget_money_and_scrubs_token():
    route = respx.put(f"{A}/campaign").mock(side_effect=[
        httpx.Response(200, json={"CampaignId": "c9", "DailyBudget": {"Amount": 250.5, "CurrencyCode": "USD"}}),
        httpx.Response(403, json={"Message": "token ttd-tok-123 not authorized"})])
    res = await _server().call_tool("update_budget", {"campaign_id": "c9", "daily_budget": 250.5, "currency": "USD"})
    assert res.structured_content["status"] == "updated"
    assert json.loads(route.calls[0].request.content) == {"CampaignId": "c9", "DailyBudget": {"Amount": 250.5, "CurrencyCode": "USD"}}
    bad = await _server().call_tool("update_budget", {"campaign_id": "c9", "daily_budget": 1, "currency": "USD"})
    assert bad.structured_content["error"] == "auth_error" and "ttd-tok-123" not in json.dumps(bad.structured_content)
