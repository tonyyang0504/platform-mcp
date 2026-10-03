import json
import re
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "deals" / "etenders_etenders_gov_za.json").read_text(encoding="utf-8"))
BASE = "https://ocds-api.etenders.gov.za/api/OCDSReleases"

# OCDS release as returned live on 2026-09-25 (documents trimmed)
REL = {
    "ocid": "ocds-9t57fa-171582", "id": "ocds-9t57fa-171582-2026-09-24", "date": "2026-09-24T00:00:00Z", "tag": ["compiled"],
    "tender": {"id": "171582", "title": "NB124/2026 ", "status": "active", "category": "Education", "province": "Gauteng",
               "description": "REQUEST FOR QUOTATION : SHE & FIRST AID TRAINING ", "value": {"amount": 0, "currency": "ZAR"},
               "tenderPeriod": {"startDate": "2026-09-24T00:00:00Z", "endDate": "2026-09-30T09:00:00Z"},
               "procuringEntity": {"id": "663", "name": "Tourism"}},
    "buyer": {"id": "663", "name": "Tourism"}, "awards": [], "contracts": [],
}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_are_search_and_get():
    assert sorted(t.name for t in await _server().list_tools()) == ["get_posting", "search_postings"]


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_required_dates_and_paging_only():
    route = respx.get(BASE).mock(return_value=httpx.Response(200, json={"releases": [REL], "links": {"next": "…"}}))
    res = await _server().call_tool("search_postings", {"query": "training", "category": "Education", "page": 2, "limit": 1})
    assert res.is_error is False
    q = dict(route.calls.last.request.url.params)
    assert set(q) == {"PageNumber", "PageSize", "dateFrom", "dateTo"} and q["PageNumber"] == "2" and q["PageSize"] == "1"
    assert re.fullmatch(r"\d{4}-\d{1,2}-01T00:00:00Z", q["dateFrom"])
    p = res.structured_content["postings"][0]
    assert p["id"] == "ocds-9t57fa-171582" and p["buyer"] == "Tourism" and p["description"].startswith("REQUEST FOR QUOTATION")
    assert p["currency"] == "ZAR" and p["deadline"] == "2026-09-30T09:00:00Z"
    assert res.structured_content["next_page"] == 3


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_by_ocid():
    respx.get(f"{BASE}/release/ocds-9t57fa-171582").mock(return_value=httpx.Response(200, json=REL))
    res = await _server().call_tool("get_posting", {"id": "ocds-9t57fa-171582"})
    assert res.is_error is False and res.structured_content["title"] == "NB124/2026 "


@pytest.mark.asyncio
@respx.mock
async def test_missing_dates_error_is_invalid_input():
    respx.get(BASE).mock(return_value=httpx.Response(400, text="dateFrom and dateTo fields are required. "))
    res = await _server().call_tool("search_postings", {})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"
