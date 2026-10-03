import base64
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

SPEC = json.loads((ROOT / "catalog" / "automotive" / "autoria.json").read_text(encoding="utf-8"))
API = "https://developers.ria.com"
CREDS = {"api_key": "ria-key-0123456789abcdef", "user_id": "12246211"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], CREDS, 50, "test"))


@pytest.mark.asyncio
async def test_search_is_not_served():
    assert sorted(t.name for t in await _server().list_tools()) == ["get_listing", "get_valuation"]


@pytest.mark.asyncio
@respx.mock
async def test_auto_info_maps_the_ad():
    route = respx.get(url__startswith=API + "/auto/info").mock(return_value=httpx.Response(200, json={
        "USD": 15500, "UAH": 620000, "title": "BMW X5 2012", "markName": "BMW", "modelName": "X5", "locationCityName": "Київ",
        "addDate": "2026-09-01 10:00:00", "autoData": {"autoId": 36756951, "year": 2012, "description": "Ідеальний стан", "race": "150 тис. км"}}))
    res = await _server().call_tool("get_listing", {"listing_id": "36756951"})
    sc = res.structured_content
    assert res.is_error is False and sc["id"] == "36756951" and sc["price"] == 15500 and sc["currency"] == "USD" and sc["year"] == 2012 and sc["make"] == "BMW"
    q = route.calls.last.request.url.params
    assert q["auto_id"] == "36756951" and q["api_key"] == "ria-key-0123456789abcdef"


@pytest.mark.asyncio
@respx.mock
async def test_valuation_posts_the_vin_as_omni_id():
    route = respx.post(url__startswith=API + "/auto/statistic-avarage-price/").mock(return_value=httpx.Response(200, json={"graphData": [{"date": "2026-08", "price": {"UAH": 156672, "USD": 4200}}]}))
    res = await _server().call_tool("get_valuation", {"vin": "TMBGP21U432674944"})
    assert res.is_error is False and res.structured_content["raw"]["graphData"][0]["price"]["USD"] == 4200
    req = route.calls.last.request
    assert json.loads(req.content) == {"langId": 4, "period": 365, "params": {"omniId": "TMBGP21U432674944"}}
    assert req.url.params["user_id"] == "12246211" and req.url.params["api_key"] == "ria-key-0123456789abcdef"


@pytest.mark.asyncio
@respx.mock
async def test_bad_key_is_an_auth_error_without_the_key():
    respx.get(url__startswith=API + "/auto/info").mock(return_value=httpx.Response(403, json={"error": "API_KEY_INVALID ria-key-0123456789abcdef"}))
    res = await _server().call_tool("get_listing", {"listing_id": "1"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "ria-key-0123456789abcdef" not in json.dumps(res.structured_content)
