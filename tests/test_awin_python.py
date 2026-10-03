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

SPEC = json.loads((ROOT / "catalog" / "ads" / "awin.json").read_text(encoding="utf-8"))
A = "https://api.awin.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_token": "awin-secret-token"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "list_accounts", "get_report"}


@pytest.mark.asyncio
@respx.mock
async def test_list_accounts_filters_advertisers_with_bearer():
    route = respx.get(f"{A}/accounts").mock(return_value=httpx.Response(200, json={"userId": 9, "accounts": [
        {"accountId": 1001, "accountName": "Shop Ltd", "accountType": "advertiser", "userRole": "admin"}]}))
    res = await _server().call_tool("list_accounts", {})
    assert res.is_error is False
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Bearer awin-secret-token"
    assert parse_qs(urlparse(str(req.url)).query) == {"type": ["advertiser"]}
    assert res.structured_content["accounts"][0]["id"] == "1001"


@pytest.mark.asyncio
@respx.mock
async def test_get_report_publisher_rows():
    route = respx.get(f"{A}/advertisers/1001/reports/publisher").mock(return_value=httpx.Response(200, json=[
        {"publisherId": 55, "publisherName": "Blog", "currency": "GBP", "impressions": 10, "clicks": 4, "totalNo": 2, "totalValue": 80.0, "totalComm": 8.0}]))
    res = await _server().call_tool("get_report", {"account_id": "1001", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    q = {k: v[0] for k, v in parse_qs(urlparse(str(route.calls[0].request.url)).query).items()}
    assert q == {"startDate": "2026-09-01", "endDate": "2026-09-07", "timezone": "UTC", "dateType": "transaction"}
    r = res.structured_content["rows"][0]
    assert (r["publisher_id"], r["spend"], r["currency"]) == ("55", 8.0, "GBP")


@pytest.mark.asyncio
@respx.mock
async def test_bad_date_and_refused_token():
    bad = await _server().call_tool("get_report", {"account_id": "1001", "date_from": "01/09/2026", "date_to": "2026-09-07"})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"
    respx.get(f"{A}/accounts").mock(return_value=httpx.Response(401, json={"error": "token awin-secret-token revoked"}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "awin-secret-token" not in json.dumps(res.structured_content)
