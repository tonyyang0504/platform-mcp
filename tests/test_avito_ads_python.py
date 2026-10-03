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

SPEC = json.loads((ROOT / "catalog" / "ads" / "avito_ads.json").read_text(encoding="utf-8"))
A = "https://api.avito.ru/ads"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "av-cid", "client_secret": "av-secret-xyz", "account_id": "4242"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post("https://api.avito.ru/token").mock(return_value=httpx.Response(200, json={"access_token": "AVT", "token_type": "Bearer", "expires_in": 86400}))


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "list_accounts", "list_campaigns", "get_report"}


@pytest.mark.asyncio
@respx.mock
async def test_list_campaigns_posts_filter_and_paging_with_bearer():
    token = _token()
    route = respx.post(f"{A}/v1/account/4242/campaigns").mock(return_value=httpx.Response(200, json={"total": 1, "campaigns": [
        {"id": 77, "name": "Осень", "status": "active", "budget": 50000, "startDate": "2026-09-01", "endDate": "2026-09-30"}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "4242", "status": "active", "limit": 50})
    assert res.is_error is False
    assert {k: v[0] for k, v in parse_qs(token.calls[0].request.content.decode()).items()} == {"grant_type": "client_credentials", "client_id": "av-cid", "client_secret": "av-secret-xyz"}
    assert route.calls[0].request.headers["Authorization"] == "Bearer AVT"
    assert json.loads(route.calls[0].request.content) == {"filter": {"statuses": ["active"]}, "limit": 50, "page": 1}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["status"], c["budget"], res.structured_content["total"]) == ("77", "active", 50000, 1)


@pytest.mark.asyncio
@respx.mock
async def test_get_report_reads_campaign_daily_points():
    _token()
    route = respx.post(f"{A}/v1/account/4242/campaigns/77/stats").mock(return_value=httpx.Response(200, json={
        "campaign": {"id": 77, "data": [{"timestamp": "2026-09-01", "views": 1000, "clicks": 12, "spend": 340, "spendBonus": 0}], "totalData": {}}, "groups": [], "creatives": []}))
    res = await _server().call_tool("get_report", {"account_id": "4242", "campaign_id": "77", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    assert json.loads(route.calls[0].request.content) == {"dateFrom": "2026-09-01", "dateTo": "2026-09-07"}
    r = res.structured_content["rows"][0]
    assert (r["date"], r["impressions"], r["spend"]) == ("2026-09-01", 1000, 340)


@pytest.mark.asyncio
@respx.mock
async def test_refused_token_does_not_leak_secret():
    respx.post("https://api.avito.ru/token").mock(return_value=httpx.Response(401, json={"error": "invalid_client", "secret": "av-secret-xyz"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "av-secret-xyz" not in json.dumps(res.structured_content)
