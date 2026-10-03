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

SPEC = json.loads((ROOT / "catalog" / "deals" / "uk_find_a_tender.json").read_text(encoding="utf-8"))
BASE = "https://www.find-tender.service.gov.uk"

# OCDS release per apidocumentation/1.0/GET-ocdsReleasePackages
RELEASE = {
    "ocid": "ocds-h6vhtk-000cb9", "id": "000123-2026", "date": "2026-09-22T08:30:00Z", "tag": ["tender"],
    "tender": {"id": "000123-2026", "title": "Supply of laboratory equipment", "description": "Framework for lab equipment.", "status": "active",
               "value": {"amount": 1200000, "currency": "GBP"}, "tenderPeriod": {"endDate": "2026-11-15T12:00:00Z"}},
    "buyer": {"name": "NHS Example Trust"},
}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_search_and_details_are_the_only_tools():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search_postings"]
    sp = next(t for t in tools if t.name == "search_postings")
    assert sp.annotations.read_only_hint is True and sp.meta["platform_mcp/endpoint"] == "/api/1.0/ocdsReleasePackages"


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_release_packages():
    respx.get(f"{BASE}/api/1.0/ocdsReleasePackages").mock(return_value=httpx.Response(200, json={
        "uri": f"{BASE}/api/1.0/ocdsReleasePackages", "version": "1.1", "publishedDate": "2026-09-24T09:00:00Z",
        "links": {"next": f"{BASE}/api/1.0/ocdsReleasePackages?cursor=MjAyNg=="}, "releases": [RELEASE]}))
    res = await _server().call_tool("search_postings", {"limit": 5})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "ocds-h6vhtk-000cb9" and p["title"] == "Supply of laboratory equipment" and p["buyer"] == "NHS Example Trust"
    assert p["budget_max"] == 1200000 and p["currency"] == "GBP" and p["deadline"] == "2026-11-15T12:00:00Z"
    q = respx.calls.last.request.url.params
    assert q["stages"] == "tender" and q["limit"] == "5"


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_reads_the_record_package():
    respx.get(f"{BASE}/api/1.0/ocdsRecordPackages/ocds-h6vhtk-000cb9").mock(return_value=httpx.Response(200, json={
        "uri": f"{BASE}/api/1.0/ocdsRecordPackages/ocds-h6vhtk-000cb9", "version": "1.1", "publishedDate": "2026-09-24T09:00:00Z",
        "records": [{"ocid": "ocds-h6vhtk-000cb9", "releases": [RELEASE], "compiledRelease": RELEASE, "versionedRelease": {}}]}))
    res = await _server().call_tool("get_posting", {"id": "ocds-h6vhtk-000cb9"})
    assert res.is_error is False and res.structured_content["id"] == "ocds-h6vhtk-000cb9" and res.structured_content["title"] == "Supply of laboratory equipment"


@pytest.mark.asyncio
@respx.mock
async def test_429_with_retry_after_is_a_rate_limited_result():
    respx.get(f"{BASE}/api/1.0/ocdsReleasePackages").mock(return_value=httpx.Response(429, headers={"Retry-After": "60"}))
    res = await _server().call_tool("search_postings", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 60
