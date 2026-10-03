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

SPEC = json.loads((ROOT / "catalog" / "sales" / "opencorporates.json").read_text(encoding="utf-8"))
BASE = "https://api.opencorporates.com/v0.4"

# shaped as the API-Reference examples: results.companies[].company, results.company
COMPANY = {"name": "BP P.L.C.", "company_number": "00102498", "jurisdiction_code": "gb", "incorporation_date": "1909-04-14",
           "registered_address_in_full": "1 St James's Square, London, SW1Y 4PD", "current_status": "Active",
           "opencorporates_url": "https://opencorporates.com/companies/gb/00102498", "industry_codes": []}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_token": "tok"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_sales_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_company", "me", "search"]
    me = next(t for t in tools if t.name == "me")
    assert me.annotations.read_only_hint is True and me.meta["platform_mcp/endpoint"] == "/account_status"


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_documented_fields_and_query_token():
    respx.get(f"{BASE}/companies/search").mock(return_value=httpx.Response(200, json={"api_version": "0.4", "results": {
        "companies": [{"company": COMPANY}], "page": 1, "per_page": 25, "total_pages": 1, "total_count": 1}}))
    res = await _server().call_tool("search", {"query": "bp", "country": "gb"})
    assert res.is_error is False
    sc = res.structured_content
    c = sc["companies"][0]
    assert c["id"] == "00102498" and c["name"] == "BP P.L.C." and c["country"] == "gb" and c["url"] == "https://opencorporates.com/companies/gb/00102498"
    assert c["founded"] == "1909-04-14" and c["raw"]["company"]["current_status"] == "Active"
    assert sc["total"] == 1 and sc["next_page"] is None
    req = respx.calls.last.request
    assert req.url.params["q"] == "bp" and req.url.params["country_code"] == "gb" and req.url.params["per_page"] == "25" and req.url.params["page"] == "1"
    assert req.url.params["api_token"] == "tok" and "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_get_company_uses_jurisdiction_and_number():
    respx.get(f"{BASE}/companies/gb/00102498").mock(return_value=httpx.Response(200, json={"api_version": "0.4", "results": {"company": COMPANY}}))
    res = await _server().call_tool("get_company", {"id": "gb/00102498"})
    assert res.is_error is False and res.structured_content["id"] == "00102498" and res.structured_content["address"] == "1 St James's Square, London, SW1Y 4PD"


@pytest.mark.asyncio
@respx.mock
async def test_bad_token_is_an_auth_error_result():
    respx.get(f"{BASE}/account_status").mock(return_value=httpx.Response(401, json={"error": "Invalid or missing API token"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
