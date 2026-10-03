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

SPEC = json.loads((ROOT / "catalog" / "ads" / "partnerize.json").read_text(encoding="utf-8"))
B = "https://api.partnerize.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"application_key": "pz-app", "user_api_key": "pz-user-secret"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "list_accounts", "list_campaigns", "get_report"}


@pytest.mark.asyncio
@respx.mock
async def test_list_campaigns_unwraps_campaign_objects_with_basic_auth():
    route = respx.get(f"{B}/user/advertiser/10l110/campaign").mock(return_value=httpx.Response(200, json={"count": 1, "campaigns": [
        {"campaign": {"campaign_id": "10l176", "title": "PHG Aff Demo", "status": "a", "default_currency": "GBP"}}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "10l110"})
    assert res.is_error is False
    assert route.calls[0].request.headers["Authorization"] == "Basic " + base64.b64encode(b"pz-app:pz-user-secret").decode()
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["name"], c["status"], c["currency"]) == ("10l176", "PHG Aff Demo", "a", "GBP")


@pytest.mark.asyncio
@respx.mock
async def test_get_report_conversions_with_day_bounds():
    route = respx.get(f"{B}/reporting/report_advertiser/campaign/10l176/conversion.json").mock(return_value=httpx.Response(200, json={"count": 1, "limit": 300, "conversions": [
        {"conversion_data": {"conversion_id": "111111l10", "conversion_time": "2026-09-02 10:00:00", "publisher_id": "111111l92", "currency": "USD",
                             "conversion_value": {"conversion_status": "pending", "value": 400, "commission": 44, "publisher_commission": 40}}}]}))
    res = await _server().call_tool("get_report", {"account_id": "x", "campaign_id": "10l176", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    q = {k: v[0] for k, v in parse_qs(urlparse(str(route.calls[0].request.url)).query).items()}
    assert q == {"start_date": "2026-09-01T00:00:00Z", "end_date": "2026-09-07T23:59:59Z", "timezone": "UTC"}
    r = res.structured_content["rows"][0]
    assert (r["conversion_id"], r["spend"], r["sales"], r["status"]) == ("111111l10", 44, 400, "pending")


@pytest.mark.asyncio
@respx.mock
async def test_refused_keys_do_not_leak():
    respx.get(f"{B}/v3/brand").mock(return_value=httpx.Response(401, json={"error": {"message": "bad key pz-user-secret"}}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "pz-user-secret" not in json.dumps(res.structured_content)
