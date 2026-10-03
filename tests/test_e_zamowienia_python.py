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

SPEC = json.loads((ROOT / "catalog" / "deals" / "e_zamowienia.json").read_text(encoding="utf-8"))
URL = "https://ezamowienia.gov.pl/mo-board/api/v1/notice"

# NoticeDto as returned live on 2026-09-25 (htmlBody trimmed)
NOTICE = {
    "clientType": "1.1.2", "orderType": "Delivery", "tenderType": "1.1.2", "noticeType": "ContractNotice",
    "noticeNumber": "2026/BZP 00438129/01", "bzpNumber": "2026/BZP 00438129", "publicationDate": "2026-09-15T09:10:55.8818825Z",
    "orderObject": "Zakup i dostawa autobusu", "cpvCode": "34121400-5 (Autobusy niskopodłogowe)", "submittingOffersDate": "2026-09-24T08:00:00Z",
    "organizationName": "Gmina Chmielnik", "organizationCity": "Chmielnik", "htmlBody": "<html>…</html>", "objectId": "08df1309-3ffa-e87c-db89-6a00017096d8",
}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_are_search_and_get():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search_postings"]


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_required_window_and_filters():
    route = respx.get(URL).mock(return_value=httpx.Response(200, json=[NOTICE]))
    res = await _server().call_tool("search_postings", {"query": "autobus", "category": "34121400-5", "limit": 10})
    assert res.is_error is False
    q = dict(route.calls.last.request.url.params)
    assert q["NoticeType"] == "ContractNotice" and q["OrderObject"] == "autobus" and q["CpvCode"] == "34121400-5" and q["PageSize"] == "10"
    assert re.fullmatch(r"\d{4}-\d{1,2}-01T00:00:00Z", q["PublicationDateFrom"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.000Z", q["PublicationDateTo"])
    p = res.structured_content["postings"][0]
    assert p["id"] == "2026/BZP 00438129/01" and p["title"] == "Zakup i dostawa autobusu" and p["buyer"] == "Gmina Chmielnik"
    assert p["deadline"] == "2026-09-24T08:00:00Z" and p["raw"]["objectId"].startswith("08df")


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_by_notice_number_and_miss():
    route = respx.get(URL).mock(side_effect=[httpx.Response(200, json=[NOTICE]), httpx.Response(200, json=[])])
    ok = await _server().call_tool("get_posting", {"id": "2026/BZP 00438129/01"})
    assert ok.is_error is False and ok.structured_content["buyer"] == "Gmina Chmielnik"
    q = dict(route.calls.last.request.url.params)
    assert q["NoticeNumber"] == "2026/BZP 00438129/01" and q["PublicationDateFrom"] == "2021-01-01T00:00:00Z" and q["PageSize"] == "1"
    miss = await _server().call_tool("get_posting", {"id": "2026/BZP 00000000/01"})
    assert miss.is_error is True and miss.structured_content["error"] == "not_found"


@pytest.mark.asyncio
@respx.mock
async def test_validation_problem_is_invalid_input():
    respx.get(URL).mock(return_value=httpx.Response(400, json={"errors": {"PublicationDateTo": ["Pole 'Publication Date To' nie może być puste."]}, "title": "One or more validation errors occurred.", "status": 400}))
    res = await _server().call_tool("search_postings", {"query": "x"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"
