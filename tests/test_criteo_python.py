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


SPEC = json.loads((ROOT / "catalog" / "ads" / "criteo.json").read_text(encoding="utf-8"))
C = "https://api.criteo.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "crit-cid", "client_secret": "critsecret", "currency": "EUR"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post(f"{C}/oauth2/token").mock(return_value=httpx.Response(200, json={"access_token": "CRT", "token_type": "Bearer", "expires_in": 900}))


@pytest.mark.asyncio
@respx.mock
async def test_client_credentials_in_the_body_and_campaign_search_filter_array():
    token = _token()
    route = respx.post(f"{C}/2026-07/marketing-solutions/campaigns/search").mock(return_value=httpx.Response(200, json={"data": [
        {"type": "Campaign", "id": "555", "attributes": {"name": "Retargeting", "advertiserId": "13", "goal": "retention", "spendLimit": {"spendLimitRenewal": "daily", "spendLimitType": "capped", "spendLimitAmount": {"value": 100.0}}}}], "errors": [], "warnings": []}))
    res = await _server().call_tool("list_campaigns", {"account_id": "13"})
    assert res.is_error is False
    assert _form(token.calls[0].request) == {"grant_type": "client_credentials", "client_id": "crit-cid", "client_secret": "critsecret"}
    assert route.calls[0].request.headers["Authorization"] == "Bearer CRT"
    assert json.loads(route.calls[0].request.content) == {"filters": {"advertiserIds": ["13"]}}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["name"], c["budget"]) == ("555", "Retargeting", 100.0)


@pytest.mark.asyncio
@respx.mock
async def test_get_report_posts_campaign_day_json_statistics():
    _token()
    route = respx.post(f"{C}/2026-07/statistics/report").mock(return_value=httpx.Response(200, json={"Rows": [
        {"CampaignId": "555", "Campaign": "Retargeting", "Day": "2026-09-01", "Currency": "EUR", "Displays": "2534", "Clicks": "35", "AdvertiserCost": "12.40"}], "Total": {}}))
    res = await _server().call_tool("get_report", {"account_id": "13", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    r = res.structured_content["rows"][0]
    assert (r["campaign_id"], r["date"], r["impressions"], r["clicks"], r["spend"]) == ("555", "2026-09-01", "2534", "35", "12.40")
    assert json.loads(route.calls[0].request.content) == {"advertiserIds": "13", "startDate": "2026-09-01", "endDate": "2026-09-07", "format": "json", "currency": "EUR",
                                                          "dimensions": ["CampaignId", "Campaign", "Day"], "metrics": ["Displays", "Clicks", "AdvertiserCost"]}


@pytest.mark.asyncio
@respx.mock
async def test_update_budget_patches_a_capped_daily_spend_limit_and_reports_rejections():
    _token()
    route = respx.patch(f"{C}/2026-07/marketing-solutions/campaigns").mock(side_effect=[
        httpx.Response(200, json={"data": [{"id": "555", "type": "Campaign"}], "errors": [], "warnings": []}),
        httpx.Response(200, json={"data": [], "errors": [{"code": "invalid", "title": "Spend limit too low", "detail": "value"}], "warnings": []})])
    res = await _server().call_tool("update_budget", {"campaign_id": "555", "daily_budget": 80})
    assert res.is_error is False and res.structured_content["status"] == "updated" and res.structured_content["campaign_id"] == "555"
    assert json.loads(route.calls[0].request.content) == {"data": [{"id": "555", "type": "Campaign", "attributes": {"spendLimit": {"spendLimitAmount": {"value": 80}, "spendLimitRenewal": "daily", "spendLimitType": "capped"}}}]}
    bad = await _server().call_tool("update_budget", {"campaign_id": "555", "daily_budget": 0.01})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_refused_client_credentials_do_not_leak_the_secret():
    respx.post(f"{C}/oauth2/token").mock(return_value=httpx.Response(400, json={"error": "invalid_client"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and "critsecret" not in json.dumps(res.structured_content)
