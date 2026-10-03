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

SPEC = json.loads((ROOT / "catalog" / "ads" / "bol_retail_media.json").read_text(encoding="utf-8"))
B = "https://api.bol.com/advertiser/sponsored-products"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "bol-cid", "client_secret": "bol-secret-123"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post("https://login.bol.com/token").mock(return_value=httpx.Response(200, json={"access_token": "JWT1", "token_type": "Bearer", "expires_in": 299}))


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "list_campaigns", "get_report"}


@pytest.mark.asyncio
@respx.mock
async def test_basic_token_then_campaign_list_filter():
    token = _token()
    route = respx.post(f"{B}/campaign-management/campaigns/list").mock(return_value=httpx.Response(200, json={"campaigns": [
        {"campaignId": "12345", "name": "Herfst", "state": "ENABLED", "startDate": "2026-09-01", "dailyBudget": {"amount": 25, "currency": "EUR"}, "campaignType": "MANUAL", "constraints": []}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "x", "status": "ENABLED", "limit": 10})
    assert res.is_error is False
    assert token.calls[0].request.headers["Authorization"] == "Basic " + base64.b64encode(b"bol-cid:bol-secret-123").decode()
    assert route.calls[0].request.headers["Authorization"] == "Bearer JWT1"
    assert json.loads(route.calls[0].request.content) == {"filter": {"states": ["ENABLED"]}, "page": 1, "pageSize": 10}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["status"], c["budget"], c["currency"]) == ("12345", "ENABLED", 25, "EUR")


@pytest.mark.asyncio
@respx.mock
async def test_get_report_campaign_entity_query():
    _token()
    route = respx.get(f"{B}/reporting/performance").mock(return_value=httpx.Response(200, json={"total": {"cost": 10.5}, "subTotals": [
        {"entityType": "CAMPAIGN", "entityId": "12345", "campaignId": "12345", "impressions": 900, "clicks": 30, "cost": 10.5, "conversions14d": 2, "sales14d": 60.0}]}))
    res = await _server().call_tool("get_report", {"account_id": "x", "campaign_id": "12345", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    q = {k: v[0] for k, v in parse_qs(urlparse(str(route.calls[0].request.url)).query).items()}
    assert q == {"entity-ids": "12345", "period-start-date": "2026-09-01", "period-end-date": "2026-09-07", "entity-type": "CAMPAIGN"}
    assert res.structured_content["rows"][0]["spend"] == 10.5


@pytest.mark.asyncio
@respx.mock
async def test_refused_credentials_do_not_leak():
    respx.post("https://login.bol.com/token").mock(return_value=httpx.Response(401, text="bad client bol-secret-123"))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "bol-secret-123" not in json.dumps(res.structured_content)
