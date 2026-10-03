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

SPEC = json.loads((ROOT / "catalog" / "sales" / "uk_companies_house.json").read_text(encoding="utf-8"))
BASE = "https://api.company-information.service.gov.uk"

# shaped as the CompanySearch / companyProfile resources document them
SEARCH_ITEM = {"company_number": "00102498", "title": "BP P.L.C.", "company_status": "active", "company_type": "plc", "date_of_creation": "1909-04-14",
               "address_snippet": "1 St James's Square, London, SW1Y 4PD",
               "address": {"address_line_1": "1 St James's Square", "locality": "London", "postal_code": "SW1Y 4PD", "country": "United Kingdom"},
               "kind": "searchresults#company", "links": {"self": "/company/00102498"}}
PROFILE = {"company_name": "BP P.L.C.", "company_number": "00102498", "company_status": "active", "type": "plc", "date_of_creation": "1909-04-14",
           "sic_codes": ["06100", "19201"], "registered_office_address": {"address_line_1": "1 St James's Square", "locality": "London", "postal_code": "SW1Y 4PD", "country": "United Kingdom"},
           "links": {"self": "/company/00102498"}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "k"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_sales_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_company", "me", "search"]
    search = next(t for t in tools if t.name == "search")
    assert search.annotations.read_only_hint is True and search.annotations.destructive_hint is False
    assert search.input_schema["required"] == ["query"] and search.output_schema["properties"]["companies"]["type"] == "array"
    assert search.title == "Search companies"


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_documented_fields_and_basic_auth():
    respx.get(f"{BASE}/search/companies").mock(return_value=httpx.Response(200, json={"items": [SEARCH_ITEM], "items_per_page": 25, "start_index": 0, "total_results": 1, "kind": "search#companies"}))
    res = await _server().call_tool("search", {"query": "bp"})
    assert res.is_error is False
    sc = res.structured_content
    c = sc["companies"][0]
    assert c["id"] == "00102498" and c["name"] == "BP P.L.C." and c["country"] == "United Kingdom" and c["founded"] == "1909-04-14"
    assert c["address"] == "1 St James's Square, London, SW1Y 4PD" and c["raw"]["links"]["self"] == "/company/00102498"
    assert sc["total"] == 1 and sc["next_page"] is None
    req = respx.calls.last.request
    assert req.url.params["q"] == "bp" and req.url.params["items_per_page"] == "25" and req.url.params["start_index"] == "0"
    # the key is the Basic user name, the password is empty
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(b"k:").decode()


@pytest.mark.asyncio
@respx.mock
async def test_get_company_maps_the_profile_resource():
    respx.get(f"{BASE}/company/00102498").mock(return_value=httpx.Response(200, json=PROFILE))
    res = await _server().call_tool("get_company", {"id": "00102498"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "00102498" and sc["name"] == "BP P.L.C." and sc["industry"] == "06100" and sc["address"] == "1 St James's Square"
    assert sc["raw"]["sic_codes"] == ["06100", "19201"]


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result():
    respx.get(f"{BASE}/company/X").mock(return_value=httpx.Response(429, headers={"Retry-After": "300"}))
    res = await _server().call_tool("get_company", {"id": "X"})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 300
