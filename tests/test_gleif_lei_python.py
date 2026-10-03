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

SPEC = json.loads((ROOT / "catalog" / "sales" / "gleif_lei.json").read_text(encoding="utf-8"))
BASE = "https://api.gleif.org/api/v1"

# JSON:API record as api.gleif.org returns it (live check 2026-09-24)
RECORD = {"type": "lei-records", "id": "HWUPKR0MPOU8FGXBT394",
          "attributes": {"lei": "HWUPKR0MPOU8FGXBT394", "entity": {
              "legalName": {"name": "Apple Inc.", "language": "en"},
              "legalAddress": {"language": "en", "addressLines": ["C/O Corporation Service Company", "Corporation Service Company, 500 N Brand Blvd Suite 1400"], "city": "Glendale", "region": "US-CA", "country": "US", "postalCode": "91203"},
              "status": "ACTIVE", "creationDate": "1977-01-03T00:00:00Z", "legalForm": {"id": "H1UM", "other": None}}},
          "links": {"self": "https://api.gleif.org/api/v1/lei-records/HWUPKR0MPOU8FGXBT394"}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_sales_vocabulary_without_credentials():
    assert SPEC["adapter"]["auth"] == {"type": "none", "fields": []}
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_company", "me", "search"]
    assert next(t for t in tools if t.name == "get_company").meta["platform_mcp/endpoint"] == "/lei-records/{id}"


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_json_api_fields_and_filters():
    respx.get(f"{BASE}/lei-records").mock(return_value=httpx.Response(200, json={
        "meta": {"goldenCopy": {"publishDate": "2026-09-24T00:00:00Z"}, "pagination": {"currentPage": 1, "perPage": 25, "from": 1, "to": 1, "total": 1, "lastPage": 1}},
        "links": {"first": "…", "last": "…"}, "data": [RECORD]}))
    res = await _server().call_tool("search", {"query": "Apple Inc.", "country": "US"})
    assert res.is_error is False
    sc = res.structured_content
    c = sc["companies"][0]
    assert c["id"] == "HWUPKR0MPOU8FGXBT394" and c["name"] == "Apple Inc." and c["country"] == "US"
    assert c["address"] == "C/O Corporation Service Company" and c["founded"] == "1977-01-03T00:00:00Z" and c["url"].endswith("/lei-records/HWUPKR0MPOU8FGXBT394")
    assert c["raw"]["attributes"]["entity"]["status"] == "ACTIVE" and sc["total"] == 1 and sc["next_page"] is None
    req = respx.calls.last.request
    assert req.url.params["filter[entity.legalName]"] == "Apple Inc." and req.url.params["filter[entity.legalAddress.country]"] == "US"
    assert req.url.params["page[size]"] == "25" and req.url.params["page[number]"] == "1" and "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_get_company_reads_the_data_root():
    respx.get(f"{BASE}/lei-records/HWUPKR0MPOU8FGXBT394").mock(return_value=httpx.Response(200, json={"data": RECORD}))
    res = await _server().call_tool("get_company", {"id": "HWUPKR0MPOU8FGXBT394"})
    assert res.is_error is False and res.structured_content["name"] == "Apple Inc." and res.structured_content["id"] == "HWUPKR0MPOU8FGXBT394"


@pytest.mark.asyncio
@respx.mock
async def test_unknown_lei_is_an_not_found_result():
    respx.get(f"{BASE}/lei-records/NOPE").mock(return_value=httpx.Response(404, json={"errors": [{"status": "404"}]}))
    res = await _server().call_tool("get_company", {"id": "NOPE"})
    assert res.is_error is True and res.structured_content["error"] == "not_found" and res.structured_content["http_status"] == 404
