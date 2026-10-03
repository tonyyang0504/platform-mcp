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


async def _names(server):
    return sorted(t.name for t in await server.list_tools())

SPEC = json.loads((ROOT / "catalog" / "ads" / "smartnews_ads.json").read_text(encoding="utf-8"))
A = "https://ads.smartnews.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "12345", "client_secret": "snsecret", "ad_account_id": "777"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post(f"{A}/api/oauth/v1/access_tokens").mock(return_value=httpx.Response(200, json={"access_token": "SNJWTTOKEN", "expires_in": 86400, "token_type": "Bearer", "scope": "ads-manager"}))


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["get_report", "list_accounts", "list_campaigns", "me", "pause_resume"]


@pytest.mark.asyncio
@respx.mock
async def test_campaigns_paging_and_micros():
    _token()
    route = respx.get(f"{A}/api/ma/v3/ad_accounts/777/campaigns").mock(return_value=httpx.Response(200, json={"data": [
        {"campaign_id": 55, "name": "Launch", "configured_status": "ACTIVE", "daily_budget_amount_micro": 10000000000, "start_date_time": "2026-09-01T00:00:00Z"}],
        "pagination": {"page": 1, "page_size": 25, "total_pages": 1, "total_objects": 1}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "777"})
    assert dict(route.calls[0].request.url.params) == {"page": "1", "page_size": "25"}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["status"], c["budget_micros"]) == ("55", "ACTIVE", 10000000000) and res.structured_content["total"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_insights_repeat_fields_and_utc_bounds():
    _token()
    route = respx.get(f"{A}/api/ma/v3/ad_accounts/777/insights/campaigns").mock(return_value=httpx.Response(200, json={"data": [
        {"type": "CAMPAIGN", "id": 55, "metadata": {"name": "Launch"}, "metrics": {"viewable_impression": 900, "click": 9, "ctr": "0.01", "cpc": "12", "budget_spent": "108"}}], "pagination": {}}))
    res = await _server().call_tool("get_report", {"account_id": "777", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    url = route.calls[0].request.url
    assert url.params.get_list("fields") == ["metadata_name", "metrics_viewable_impression", "metrics_click", "metrics_ctr", "metrics_cpc", "metrics_budget_spent"]
    assert (url.params["since"], url.params["until"]) == ("2026-09-01T00:00:00Z", "2026-09-07T23:59:59Z")
    r = res.structured_content["rows"][0]
    assert (r["campaign_id"], r["impressions"], r["spend"]) == ("55", 900, "108")


@pytest.mark.asyncio
@respx.mock
async def test_merge_patch_status_and_refused_credentials():
    _token()
    route = respx.patch(f"{A}/api/ma/v3/ad_accounts/777/campaigns/55").mock(return_value=httpx.Response(200, json={"campaign_id": 55, "configured_status": "PAUSED"}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "55", "action": "pause"})
    assert route.calls[0].request.headers["Content-Type"] == "application/merge-patch+json"
    assert json.loads(route.calls[0].request.content) == {"configured_status": "PAUSED"}
    assert res.structured_content["status"] == "PAUSED"
    respx.post(f"{A}/api/oauth/v1/access_tokens").mock(return_value=httpx.Response(401, json={"message": "bad secret snsecret"}))
    fresh = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "12345", "client_secret": "snsecret"}, 50, "test")
    bad = await build_server(SPEC, transport=fresh).call_tool("me", {})
    assert bad.structured_content["error"] == "auth_error" and "snsecret" not in json.dumps(bad.structured_content)
