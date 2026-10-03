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

SPEC = json.loads((ROOT / "catalog" / "ads" / "mercado_ads.json").read_text(encoding="utf-8"))
A = "https://api.mercadolibre.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"client_id": "mlcid", "client_secret": "mlsecret", "refresh_token": "TG-first"}, 50, "test")
    return build_server(SPEC, transport=t)


def _token(rt="TG-second"):
    return respx.post(f"{A}/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "APP_USR-1", "expires_in": 21600, "refresh_token": rt}))


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["get_report", "list_accounts", "list_campaigns", "me"]


@pytest.mark.asyncio
@respx.mock
async def test_advertisers_use_api_version_1_and_pads():
    token = _token()
    route = respx.get(f"{A}/advertising/advertisers").mock(return_value=httpx.Response(200, json={"advertisers": [{"advertiser_id": 111, "site_id": "MLM", "advertiser_name": "Advertiser BBB", "account_name": "MLM - XYZ"}]}))
    res = await _server().call_tool("list_accounts", {})
    assert _form(token.calls[0].request)["refresh_token"] == "TG-first"
    req = route.calls[0].request
    assert req.url.params["product_id"] == "PADS" and req.headers["Api-Version"] == "1"
    assert res.structured_content["accounts"][0] == {"id": "111", "name": "Advertiser BBB", "raw": {"advertiser_id": 111, "site_id": "MLM", "advertiser_name": "Advertiser BBB", "account_name": "MLM - XYZ"}}


@pytest.mark.asyncio
@respx.mock
async def test_campaigns_status_filter_and_report_metrics():
    _token()
    route = respx.get(f"{A}/advertising/advertisers/111/product_ads/campaigns").mock(return_value=httpx.Response(200, json={"paging": {"total": 1, "offset": 0, "limit": 25}, "results": [
        {"id": 7, "name": "Crecimiento A", "status": "active", "budget": 1500.0, "currency_id": "MXN", "metrics": {"clicks": 10, "prints": 900, "cost": 55.5, "acos": 9.1, "total_amount": 600.0}}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "111", "status": "active"})
    assert route.calls[0].request.headers["Api-Version"] == "2"
    assert "filters[status]=active" in str(route.calls[0].request.url)
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["budget"], c["currency"]) == ("7", 1500.0, "MXN") and res.structured_content["total"] == 1
    rep = await _server().call_tool("get_report", {"account_id": "111", "date_from": "2026-07-01", "date_to": "2026-07-31", "campaign_id": "7"})
    p = route.calls[1].request.url.params
    assert (p["date_from"], p["date_to"], p["filters[campaign_ids]"], p["metrics"]) == ("2026-07-01", "2026-07-31", "7", "clicks,prints,ctr,cost,cpc,acos,units_quantity,total_amount")
    assert rep.structured_content["rows"][0]["spend"] == 55.5


@pytest.mark.asyncio
@respx.mock
async def test_missing_product_ads_permission_is_not_found_and_secret_scrubbed():
    _token()
    respx.get(f"{A}/advertising/advertisers").mock(return_value=httpx.Response(404, json={"message": "No permissions found for user_id"}))
    res = await _server().call_tool("list_accounts", {})
    assert res.structured_content["error"] == "not_found"
    respx.post(f"{A}/oauth/token").mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "detail": "TG-first mlsecret"}))
    bad = await _server().call_tool("me", {})
    assert bad.structured_content["error"] == "auth_error"
    assert "TG-first" not in json.dumps(bad.structured_content) and "mlsecret" not in json.dumps(bad.structured_content)
