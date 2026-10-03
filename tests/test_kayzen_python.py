import base64
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ads" / "kayzen.json").read_text(encoding="utf-8"))
B = "https://api.kayzen.io"
BASIC = base64.b64encode(b"kz-key:kz-api-secret").decode()


def _server():
    creds = {"api_basic": BASIC, "username": "ops@example.com", "password": "PASSWORD-kz", "advertiser_id": "108993"}
    return build_server(SPEC, transport=Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds, 50, "test"))


def _token():
    return respx.post(f"{B}/v1/authentication/token").mock(return_value=httpx.Response(200, json={"access_token": "ACCESS-kz", "expires_in": "1799", "scope": ""}))


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "list_campaigns", "get_report", "update_budget", "pause_resume"}


@pytest.mark.asyncio
@respx.mock
async def test_password_grant_with_basic_header_then_bearer():
    tok = _token()
    me = respx.get(f"{B}/v1/balance").mock(return_value=httpx.Response(200, json={"advertiser": {"warning": "ok", "balance": "10000.50"}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["advertiser"]["balance"] == "10000.50"
    login = tok.calls[0].request
    assert login.headers["Authorization"] == f"Basic {BASIC}"
    assert json.loads(login.content) == {"grant_type": "password", "username": "ops@example.com", "password": "PASSWORD-kz"}
    assert me.calls[0].request.headers["Authorization"] == "Bearer ACCESS-kz"
    assert me.calls[0].request.url.params["advertiser_id"] == "108993"


@pytest.mark.asyncio
@respx.mock
async def test_list_campaigns_pages_and_maps():
    _token()
    route = respx.get(url__startswith=f"{B}/v1/campaigns").mock(return_value=httpx.Response(200, json={
        "data": [{"id": 135858, "name": "BC_play_test", "status": "paused", "day_budget": 200, "start_time": "2019-01-28T12:35:31.000Z", "end_time": "2038-01-01T00:00:00.000Z"}],
        "meta": {"current_page": 2, "total_pages": 2, "total_entries": 26}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "108993", "page": 2, "limit": 25})
    q = {k: v[0] for k, v in parse_qs(urlparse(str(route.calls[0].request.url)).query).items()}
    assert q == {"advertiser_id": "108993", "page": "2", "per_page": "25"}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["status"], c["budget"]) == ("135858", "paused", 200) and res.structured_content["total"] == 26


@pytest.mark.asyncio
@respx.mock
async def test_report_body_and_campaign_filter():
    _token()
    route = respx.post(f"{B}/v1/report_data").mock(return_value=httpx.Response(200, json={"headers": [], "data": [
        {"day": "2026-09-01", "campaign_id": 138939, "campaign_name": "UA", "impressions": 1000, "clicks": 12, "advertiser_spend": 3.5, "ctr": 0.012}]}))
    res = await _server().call_tool("get_report", {"account_id": "108993", "campaign_id": "138939", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False and res.structured_content["rows"][0]["spend"] == 3.5
    assert json.loads(route.calls[0].request.content) == {
        "advertiser_id": 108993, "start_date": "2026-09-01", "end_date": "2026-09-07", "metrics": ["impressions", "clicks", "advertiser_spend", "ctr"],
        "group_by": ["day", "campaign_id", "campaign_name"], "filters": {"campaign_id": [138939]}, "per_page": 1000, "time_zone": "UTC"}


@pytest.mark.asyncio
@respx.mock
async def test_budget_patch_and_status_put_wire_shape():
    _token()
    patch = respx.patch(f"{B}/v1/campaigns/135858").mock(return_value=httpx.Response(200, json={}))
    put = respx.put(f"{B}/v1/campaigns/135858/status").mock(return_value=httpx.Response(200, json={}))
    s = _server()
    res = await s.call_tool("update_budget", {"campaign_id": "135858", "daily_budget": 250})
    assert res.is_error is False and res.structured_content["status"] == "updated"
    assert json.loads(patch.calls[0].request.content) == {"data": {"campaign": {"day_budget": 250}}}
    assert (await s.call_tool("update_budget", {"campaign_id": "135858", "daily_budget": 12.5})).is_error is True and patch.call_count == 1
    await s.call_tool("pause_resume", {"campaign_id": "135858", "action": "resume"})
    assert json.loads(put.calls[0].request.content) == {"status": "running"}
