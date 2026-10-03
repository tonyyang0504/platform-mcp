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

SPEC = json.loads((ROOT / "catalog" / "automotive" / "autotrader_uk.json").read_text(encoding="utf-8"))
API = "https://api.autotrader.co.uk"
CREDS = {"key": "at-key-0123456789", "secret": "at-secret-0123456789", "advertiser_id": "123456"}
ROW = {"vehicle": {"make": "Hyundai", "model": "i10", "vin": "NLHDN51ALPZ180431", "ownershipCondition": "Used", "odometerReadingMiles": 20703, "yearOfManufacture": "2022"},
       "advertiser": {"advertiserId": "11386", "name": "Dealer 590987", "location": {"town": "MANCHESTER"}},
       "adverts": {"retailAdverts": {"suppliedPrice": {"amountGBP": 10200}}},
       "metadata": {"stockId": "8a46a1ac", "searchId": "202606259954923", "dateOnForecourt": "2026-06-25"}}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], CREDS, 50, "test"))


def _login():
    return respx.post(API + "/authenticate").mock(return_value=httpx.Response(200, json={"access_token": "at-access-token", "expires_at": "2026-10-01T13:06:30.625Z"}))


@pytest.mark.asyncio
@respx.mock
async def test_search_logs_in_with_form_key_secret_and_filters_stock():
    login = _login()
    route = respx.get(url__startswith=API + "/search").mock(return_value=httpx.Response(200, json={"results": [ROW], "totalResults": 1}))
    res = await _server().call_tool("search_listings", {"make": "Hyundai", "model": "i10", "price_max": 12000, "mileage_max": 30000, "condition": "used", "location": "M154FN"})
    assert res.is_error is False, res.structured_content
    row = res.structured_content["listings"][0]
    assert row["id"] == "202606259954923" and row["price"] == 10200 and row["currency"] == "GBP" and row["mileage_unit"] == "miles" and row["location"] == "MANCHESTER"
    body = login.calls.last.request.content.decode()
    assert "key=at-key-0123456789" in body and "secret=at-secret-0123456789" in body
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer at-access-token"
    q = req.url.params
    assert q["advertiserId"] == "123456" and q["standardMake"] == "Hyundai" and q["maxSuppliedPrice"] == "12000" and q["ownershipCondition"] == "Used" and q["postcode"] == "M154FN"


@pytest.mark.asyncio
@respx.mock
async def test_vin_decode_and_valuation_use_the_vehicles_api():
    _login()
    respx.get(url__startswith=API + "/vehicles").mock(side_effect=lambda req: httpx.Response(200, json={"results": [{
        "vehicle": {"vin": "WVWZZZE1ZMP081246", "make": "Volkswagen", "model": "ID.3", "trim": "Life", "bodyType": "Hatchback", "fuelType": "Electric", "derivative": "Pro Performance 58kWh"},
        **({"valuations": {"trade": {"amountGBP": 8446}, "partExchange": {"amountGBP": 8230}, "retail": {"amountGBP": 10802}, "private": {"amountGBP": 9380}}} if req.url.params.get("valuations") == "true" else {})}]}))
    dec = await _server().call_tool("decode_vin", {"vin": "WVWZZZE1ZMP081246"})
    assert dec.is_error is False and dec.structured_content["make"] == "Volkswagen" and dec.structured_content["body"] == "Hatchback"
    val = await _server().call_tool("get_valuation", {"vin": "WVWZZZE1ZMP081246", "mileage": 8000})
    assert val.is_error is False and (val.structured_content["low"], val.structured_content["mid"], val.structured_content["high"]) == (8446, 9380, 10802)


@pytest.mark.asyncio
@respx.mock
async def test_get_listing_by_search_id():
    _login()
    route = respx.get(url__startswith=API + "/search").mock(return_value=httpx.Response(200, json={"results": [ROW], "totalResults": 1}))
    res = await _server().call_tool("get_listing", {"listing_id": "202606259954923"})
    assert res.is_error is False and res.structured_content["vin"] == "NLHDN51ALPZ180431"
    assert route.calls.last.request.url.params["searchId"] == "202606259954923"
