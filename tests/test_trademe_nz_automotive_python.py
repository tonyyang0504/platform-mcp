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

SPEC = json.loads((ROOT / "catalog" / "automotive" / "trademe_nz.json").read_text(encoding="utf-8"))
API = "https://api.trademe.co.nz/v1"
CREDS = {"consumer_key": "4E0D082355116884742E5F33B8A199F411", "consumer_secret": "160FCF77971DC92A38596288DB071A8CA5"}
AUTH = "OAuth oauth_consumer_key=4E0D082355116884742E5F33B8A199F411, oauth_signature_method=PLAINTEXT, oauth_signature=160FCF77971DC92A38596288DB071A8CA5%26"
CAR = {"ListingId": 4912345678, "Title": "Toyota Corolla 2018", "Make": "Toyota", "Model": "Corolla", "Year": 2018, "StartPrice": 15990,
       "Odometer": 82000, "Region": "Auckland", "DealerName": "Acme Motors", "StartDate": "/Date(1790200000000)/"}


def _server():
    return build_server(SPEC, transport=Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], CREDS, 50, "test"))


@pytest.mark.asyncio
async def test_tools_are_search_and_get():
    assert sorted(t.name for t in await _server().list_tools()) == ["get_listing", "search_listings"]


@pytest.mark.asyncio
@respx.mock
async def test_used_motors_search_maps_filters_and_rows():
    route = respx.get(url__startswith=API + "/Search/Motors/Used.json").mock(return_value=httpx.Response(200, json={"TotalCount": 40, "List": [CAR]}))
    res = await _server().call_tool("search_listings", {"make": "Toyota", "model": "Corolla", "year_min": 2015, "price_max": 20000, "mileage_max": 100000, "condition": "used", "limit": 50})
    assert res.is_error is False, res.structured_content
    row = res.structured_content["listings"][0]
    assert row["id"] == "4912345678" and row["make"] == "Toyota" and row["price"] == 15990 and row["currency"] == "NZD" and row["mileage_unit"] == "km"
    assert row["dealer"] == "Acme Motors" and res.structured_content["total"] == 40
    req = route.calls.last.request
    assert req.headers["Authorization"] == AUTH
    q = req.url.params
    assert q["make"] == "Toyota" and q["year_min"] == "2015" and q["price_max"] == "20000" and q["odometer_max"] == "100000" and q["condition"] == "Used" and q["rows"] == "25"


@pytest.mark.asyncio
@respx.mock
async def test_get_listing_reads_the_listing_body():
    respx.get(API + "/Listings/4912345678.json").mock(return_value=httpx.Response(200, json={**CAR, "Body": "One owner"}))
    res = await _server().call_tool("get_listing", {"listing_id": "4912345678"})
    assert res.is_error is False and res.structured_content["description"] == "One owner"


@pytest.mark.asyncio
@respx.mock
async def test_bad_signature_is_an_auth_error_without_the_secret():
    respx.get(url__startswith=API + "/Search/Motors/Used.json").mock(return_value=httpx.Response(401, json={"ErrorDescription": "Invalid signature 160FCF77971DC92A38596288DB071A8CA5"}))
    res = await _server().call_tool("search_listings", {"query": "ute"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "160FCF77971DC92A38596288DB071A8CA5" not in json.dumps(res.structured_content)
