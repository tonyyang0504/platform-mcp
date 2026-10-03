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

SPEC = json.loads((ROOT / "catalog" / "deals" / "contracts_finder.json").read_text(encoding="utf-8"))
BASE = "https://www.contractsfinder.service.gov.uk"

# OCDS release as documented on GET-Published-Notice-OCDS-Search / GET-Published-OCDS-Record
RELEASE = {
    "ocid": "ocds-b5fd17-1a2b3c", "id": "ocds-b5fd17-1a2b3c-2026-09-20T10:00:00Z", "language": "en", "date": "2026-09-20T10:00:00Z", "tag": ["tender"],
    "tender": {"id": "t1", "title": "Provision of cloud hosting", "description": "Managed hosting for the council's web estate.", "status": "active",
               "value": {"amount": 250000, "currency": "GBP"}, "tenderPeriod": {"endDate": "2026-10-30T12:00:00Z"}},
    "buyer": {"name": "Example Borough Council"},
}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_search_and_details_are_the_only_tools():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search_postings"]
    assert all(t.annotations.read_only_hint is True for t in tools)
    gp = next(t for t in tools if t.name == "get_posting")
    assert gp.input_schema["required"] == ["id"] and gp.meta["platform_mcp/endpoint"] == "/Published/OCDS/Release/{id}"
    assert "submit_bid" in SPEC["adapter"]["not_offered"] and "me" in SPEC["adapter"]["not_offered"]


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_ocds_releases_and_fixes_the_tender_stage():
    respx.get(f"{BASE}/Published/Notices/OCDS/Search").mock(return_value=httpx.Response(200, json={
        "uri": f"{BASE}/Published/Notices/OCDS/Search?limit=10", "version": "1.1", "publishedDate": "2026-09-24T09:00:00Z",
        "publisher": {"name": "Contracts Finder", "scheme": "GB-GOV", "uid": "CF", "uri": BASE}, "links": {"next": f"{BASE}/Published/Notices/OCDS/Search?cursor=abc"},
        "releases": [RELEASE]}))
    res = await _server().call_tool("search_postings", {"query": "hosting", "limit": 10})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "ocds-b5fd17-1a2b3c-2026-09-20T10:00:00Z" and p["raw"]["ocid"] == "ocds-b5fd17-1a2b3c" and p["title"] == "Provision of cloud hosting" and p["buyer"] == "Example Borough Council"
    assert p["budget_max"] == 250000 and p["currency"] == "GBP" and p["deadline"] == "2026-10-30T12:00:00Z" and p["posted_at"] == "2026-09-20T10:00:00Z"
    q = respx.calls.last.request.url.params
    assert q["stages"] == "tender" and q["limit"] == "10" and "keyword" not in q and "query" not in q


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_reads_the_release_package():
    rid = RELEASE["id"]
    respx.get(f"{BASE}/Published/OCDS/Release/{rid}").mock(return_value=httpx.Response(200, json={
        "uri": f"{BASE}/Published/Notice/releases/{rid}.json", "publishedDate": "2026-09-24T09:00:00Z", "version": "1.1", "releases": [RELEASE]}))
    res = await _server().call_tool("get_posting", {"id": rid})
    assert res.is_error is False
    assert res.structured_content["title"] == "Provision of cloud hosting" and res.structured_content["buyer"] == "Example Borough Council" and res.structured_content["raw"]["tender"]["status"] == "active"


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_403_is_an_auth_or_rate_error_result():
    # the API pages use HTTP 403 for 'request rate limit may have been exceeded'; a 403 with rate-limit wording is
    # rate_limited (forge stress test 2026-10; it used to be reported as a credential problem)
    respx.get(f"{BASE}/Published/Notices/OCDS/Search").mock(return_value=httpx.Response(403, text="rate limit"))
    res = await _server().call_tool("search_postings", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["http_status"] == 403
