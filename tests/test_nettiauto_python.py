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

SPEC = json.loads((ROOT / "catalog" / "automotive" / "nettiauto.json").read_text(encoding="utf-8"))
API = "https://api.nettix.fi/rest/car"
CREDS = {"client_id": "nx-client", "client_secret": "nx-secret-0123456789"}
AD = {"id": "12345678", "adUrl": "https://www.nettiauto.com/volvo/v60/12345678", "userName": "Autotalo Oy", "dateCreated": "2026-09-20T10:43:40Z",
      "make": {"id": 4, "name": "Volvo"}, "model": {"id": 55, "name": "V60"}, "year": 2019, "price": 23900, "kilometers": 88000,
      "town": {"id": 1, "fi": "Helsinki", "en": "Helsinki"}}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], CREDS, 50, "test"))


def _token():
    return respx.post("https://auth.nettix.fi/oauth2/token").mock(return_value=httpx.Response(200, json={"access_token": "eyJ.nettix.jwt", "expires_in": 86400, "token_type": "bearer"}))


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_the_minted_jwt_as_x_access_token():
    tok = _token()
    route = respx.get(url__startswith=API + "/search").mock(return_value=httpx.Response(200, json=[AD]))
    res = await _server().call_tool("search_listings", {"query": "V60", "make": "4", "year_min": 2017, "price_max": 30000, "mileage_max": 100000, "limit": 10})
    assert res.is_error is False, res.structured_content
    row = res.structured_content["listings"][0]
    assert row["id"] == "12345678" and row["make"] == "Volvo" and row["model"] == "V60" and row["location"] == "Helsinki" and row["price"] == 23900
    req = route.calls.last.request
    assert req.headers["X-Access-Token"] == "eyJ.nettix.jwt" and "Authorization" not in req.headers
    q = req.url.params
    assert q["searchText"] == "V60" and q["make"] == "4" and q["yearFrom"] == "2017" and q["priceTo"] == "30000" and q["kilometersTo"] == "100000" and q["rows"] == "10"
    assert b"grant_type=client_credentials" in tok.calls.last.request.content


@pytest.mark.asyncio
@respx.mock
async def test_get_listing_reads_the_ad():
    _token()
    respx.get(API + "/ad/12345678").mock(return_value=httpx.Response(200, json={**AD, "vin": "YV1ZW72UDK1234567", "description": "Huollettu"}))
    res = await _server().call_tool("get_listing", {"listing_id": "12345678"})
    assert res.is_error is False and res.structured_content["vin"] == "YV1ZW72UDK1234567"
