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

SPEC = json.loads((ROOT / "catalog" / "ads" / "admob.json").read_text(encoding="utf-8"))
A = "https://admob.googleapis.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "gcid", "client_secret": "gsecret", "refresh_token": "1//admobrefresh"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post("https://oauth2.googleapis.com/token").mock(return_value=httpx.Response(200, json={"access_token": "ya29.AM", "expires_in": 3599}))


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["get_report", "list_accounts", "me"]


@pytest.mark.asyncio
@respx.mock
async def test_list_accounts_uses_publisher_id_and_refresh_grant():
    token = _token()
    respx.get(f"{A}/v1/accounts").mock(return_value=httpx.Response(200, json={"account": [{"name": "accounts/pub-9876543210987654", "publisherId": "pub-9876543210987654", "reportingTimeZone": "America/Los_Angeles", "currencyCode": "USD"}]}))
    res = await _server().call_tool("list_accounts", {})
    assert _form(token.calls[0].request) == {"grant_type": "refresh_token", "refresh_token": "1//admobrefresh", "client_id": "gcid", "client_secret": "gsecret"}
    a = res.structured_content["accounts"][0]
    assert (a["id"], a["currency"]) == ("pub-9876543210987654", "USD")


@pytest.mark.asyncio
@respx.mock
async def test_network_report_splits_dates_and_drops_header_and_footer():
    _token()
    route = respx.post(f"{A}/v1/accounts/pub-1/networkReport:generate").mock(return_value=httpx.Response(200, json=[
        {"header": {"dateRange": {}, "localizationSettings": {"currencyCode": "USD"}}},
        {"row": {"dimensionValues": {"DATE": {"value": "20260901"}, "APP": {"value": "ca-app-pub-1~2", "displayLabel": "My App"}},
                 "metricValues": {"IMPRESSIONS": {"integerValue": "3440"}, "CLICKS": {"integerValue": "31"}, "ESTIMATED_EARNINGS": {"microsValue": "6381903"}}}},
        {"footer": {"matchingRowCount": "1"}}]))
    res = await _server().call_tool("get_report", {"account_id": "pub-1", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    body = json.loads(route.calls[0].request.content)
    assert body["reportSpec"]["dateRange"] == {"startDate": {"year": 2026, "month": 9, "day": 1}, "endDate": {"year": 2026, "month": 9, "day": 7}}
    assert body["reportSpec"]["dimensions"] == ["DATE", "APP"]
    rows = res.structured_content["rows"]
    assert len(rows) == 1 and rows[0]["date"] == "20260901" and rows[0]["impressions"] == "3440" and rows[0]["earnings_micros"] == "6381903"


@pytest.mark.asyncio
@respx.mock
async def test_bad_date_is_invalid_input_and_denied_token_is_scrubbed():
    _token()
    bad = await _server().call_tool("get_report", {"account_id": "pub-1", "date_from": "Sept 1", "date_to": "2026-09-07"})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"
    respx.post("https://oauth2.googleapis.com/token").mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "detail": "1//admobrefresh"}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "1//admobrefresh" not in json.dumps(res.structured_content)
