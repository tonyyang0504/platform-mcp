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

SPEC = json.loads((ROOT / "catalog" / "automotive" / "marktplaats.json").read_text(encoding="utf-8"))
API = "https://api.marktplaats.nl"
CREDS = {"client_id": "mp-client", "client_secret": "mp-secret-0123456789", "category_id": "91"}
HIT = {"_links": {"mp:advertisement-website-link": {"href": "http://link.marktplaats.nl/m459", "type": "text/html"}},
       "itemId": "m459", "title": "Volkswagen Golf 1.4 TSI", "categoryId": 91, "priceModel": {"modelType": "fixed", "askingPrice": 1234500},
       "seller": {"sellerId": 231, "sellerName": "Autobedrijf X"}}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], CREDS, 50, "test"))


def _token():
    return respx.post("https://auth.marktplaats.nl/accounts/oauth/token").mock(return_value=httpx.Response(200, json={"access_token": "mp-access", "token_type": "bearer", "expires_in": 86400}))


@pytest.mark.asyncio
@respx.mock
async def test_search_uses_a_client_token_and_offset_paging():
    _token()
    route = respx.get(url__startswith=API + "/v1/search").mock(return_value=httpx.Response(200, json={"_embedded": {"mp:search-result": [HIT]}, "totalCount": 61}))
    res = await _server().call_tool("search_listings", {"query": "golf", "location": "1000AB", "page": 3, "limit": 20})
    assert res.is_error is False, res.structured_content
    row = res.structured_content["listings"][0]
    assert row["id"] == "m459" and row["dealer"] == "Autobedrijf X" and row["url"] == "http://link.marktplaats.nl/m459" and res.structured_content["total"] == 61
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer mp-access"
    q = req.url.params
    assert q["query"] == "golf" and q["categoryId"] == "91" and q["postCode"] == "1000AB" and q["offset"] == "40" and q["limit"] == "20"


@pytest.mark.asyncio
@respx.mock
async def test_get_listing_reads_an_advertisement():
    _token()
    respx.get(API + "/v1/advertisements/m459").mock(return_value=httpx.Response(200, json={**HIT, "description": "APK tot 2027"}))
    res = await _server().call_tool("get_listing", {"listing_id": "m459"})
    assert res.is_error is False and res.structured_content["description"] == "APK tot 2027"
