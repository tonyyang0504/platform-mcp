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

SPEC = json.loads((ROOT / "catalog" / "ads" / "kelkoo_group.json").read_text(encoding="utf-8"))
B = "https://api.kelkoogroup.net/merchant/statistics/v1"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"jwt": "kk-jwt-secret"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "list_campaigns", "get_report"}


@pytest.mark.asyncio
@respx.mock
async def test_list_campaigns_top_level_array_with_bearer():
    route = respx.get(f"{B}/my-campaigns").mock(return_value=httpx.Response(200, json=[{"campaignId": 1000000000, "campaignName": "Example.fr", "websiteUrl": "http://www.example.fr", "country": "fr"}]))
    res = await _server().call_tool("list_campaigns", {"account_id": "x"})
    assert res.is_error is False
    assert route.calls[0].request.headers["Authorization"] == "Bearer kk-jwt-secret"
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["name"], c["country"]) == ("1000000000", "Example.fr", "fr")


@pytest.mark.asyncio
@respx.mock
async def test_get_report_category_rows():
    route = respx.get(f"{B}/category/1000000000").mock(return_value=httpx.Response(200, json=[
        {"campaignId": 1000000000, "date": "2021-03-15", "catId": 100305123, "catName": "Games", "deviceType": "Mobile", "currency": "EUR", "clicks": 7, "cost": 1.3566}]))
    res = await _server().call_tool("get_report", {"account_id": "x", "campaign_id": "1000000000", "date_from": "2021-03-15", "date_to": "2021-03-16"})
    assert res.is_error is False
    assert parse_qs(urlparse(str(route.calls[0].request.url)).query) == {"startDate": ["2021-03-15"], "endDate": ["2021-03-16"]}
    r = res.structured_content["rows"][0]
    assert (r["date"], r["clicks"], r["spend"], r["currency"]) == ("2021-03-15", 7, 1.3566, "EUR")


@pytest.mark.asyncio
@respx.mock
async def test_report_needs_campaign_and_refusal_does_not_leak():
    bad = await _server().call_tool("get_report", {"account_id": "x", "date_from": "2021-03-15", "date_to": "2021-03-16"})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"
    respx.get(f"{B}/my-campaigns").mock(return_value=httpx.Response(401, text="invalid jwt kk-jwt-secret"))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "kk-jwt-secret" not in json.dumps(res.structured_content)
