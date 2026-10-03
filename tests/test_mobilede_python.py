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

SPEC = json.loads((ROOT / "catalog" / "automotive" / "mobilede.json").read_text(encoding="utf-8"))
API = "https://services.mobile.de/search-api"
CREDS = {"username": "dealer-api", "password": "md-pass-1234567"}
AD = {"mobileAdId": "15012", "make": "ABARTH", "model": "500", "condition": "USED", "mileage": 500, "firstRegistration": "202007",
      "detailPageUrl": "https://suchen.mobile.de/auto-inserat/abarth-500/15012.html?source=api", "creationDate": "2024-04-26T02:35:10+02:00",
      "price": {"consumerPriceGross": "1000.00", "type": "FIXED", "currency": "EUR"}}


def _server():
    a = SPEC["adapter"]
    s = build_server(SPEC, transport=Transport(a["base_url"], a["auth"], CREDS, 50, "test"))
    return s


@pytest.mark.asyncio
@respx.mock
async def test_search_uses_basic_auth_json_media_type_and_classification():
    route = respx.get(url__startswith=API + "/search").mock(return_value=httpx.Response(200, json={"total": 1813062, "currentPage": 1, "maxPages": 20, "pageSize": 20, "ads": [AD]}))
    res = await _server().call_tool("search_listings", {"make": "AUDI", "model": "A4", "year_min": 2018, "year_max": 2020, "price_max": 30000, "mileage_max": 40000, "condition": "used", "location": "DE"})
    assert res.is_error is False, res.structured_content
    row = res.structured_content["listings"][0]
    assert row["id"] == "15012" and row["make"] == "ABARTH" and row["currency"] == "EUR" and row["url"].endswith("15012.html?source=api")
    assert res.structured_content["total"] == 1813062
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(b"dealer-api:md-pass-1234567").decode()
    assert req.headers["Accept"] == "application/vnd.de.mobile.api+json"
    q = req.url.params
    assert q["classification"] == "refdata/classes/Car/makes/AUDI" and q["modelDescription"] == "A4" and q["condition"] == "USED"
    assert q["firstRegistrationDate.min"] == "2018-01" and q["firstRegistrationDate.max"] == "2020-12" and q["mileage.max"] == "40000" and q["country"] == "DE"


@pytest.mark.asyncio
@respx.mock
async def test_get_listing_by_ad_key():
    respx.get(API + "/ad/15012").mock(return_value=httpx.Response(200, json={**AD, "vin": "ZFA31200000123456", "plainTextDescription": "Top"}))
    res = await _server().call_tool("get_listing", {"listing_id": "15012"})
    assert res.is_error is False and res.structured_content["vin"] == "ZFA31200000123456" and res.structured_content["description"] == "Top"


@pytest.mark.asyncio
@respx.mock
async def test_wrong_ad_key_is_not_found():
    respx.get(API + "/ad/1").mock(return_value=httpx.Response(404, json={}))
    res = await _server().call_tool("get_listing", {"listing_id": "1"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"
