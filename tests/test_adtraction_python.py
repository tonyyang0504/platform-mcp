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

SPEC = json.loads((ROOT / "catalog" / "ads" / "adtraction.json").read_text(encoding="utf-8"))
B = "https://api.adtraction.net/v2"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_token": "adt-secret-token"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list_is_me_and_get_report():
    tools = {t.name for t in await _server().list_tools()}
    assert tools == {"me", "get_report"}


@pytest.mark.asyncio
@respx.mock
async def test_me_sends_x_token():
    route = respx.get(f"{B}/advertiser/account/").mock(return_value=httpx.Response(200, json={"programId": 52561763, "programName": "Ferratum SE", "currency": "SEK", "market": "SE"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["programName"] == "Ferratum SE"
    assert route.calls[0].request.headers["X-Token"] == "adt-secret-token"


@pytest.mark.asyncio
@respx.mock
async def test_get_report_posts_daily_statistics_window():
    route = respx.post(f"{B}/advertiser/statistics/days/").mock(return_value=httpx.Response(200, json=[
        {"date": "2026-09-01", "clicks": 120, "clicksUnique": 100, "cost": 45.5, "impressions": 3000, "orderValue": 900, "leads": 2, "sales": 7}]))
    res = await _server().call_tool("get_report", {"account_id": "x", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    assert json.loads(route.calls[0].request.content) == {"fromDate": "2026-09-01", "toDate": "2026-09-07", "transactionStatus": 3}
    r = res.structured_content["rows"][0]
    assert (r["date"], r["clicks"], r["spend"], r["sales"]) == ("2026-09-01", 120, 45.5, 7)


@pytest.mark.asyncio
@respx.mock
async def test_refused_token_is_auth_error_without_leak():
    respx.get(f"{B}/advertiser/account/").mock(return_value=httpx.Response(401, json={"message": "invalid token adt-secret-token"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "adt-secret-token" not in json.dumps(res.structured_content)
