import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "deals" / "sam_gov.json").read_text(encoding="utf-8"))
API = "https://api.sam.gov/opportunities/v2/search"
OPP = {"noticeId": "5b345bbb7127b91a3ad577b203fc6f68", "title": "Historic Office Renovation ", "solicitationNumber": " 47PF0018R0023 ",
       "fullParentPathName": "GENERAL SERVICES ADMINISTRATION.PUBLIC BUILDINGS SERVICE", "postedDate": "2026-09-04", "type": "Combined Synopsis/Solicitation",
       "responseDeadLine": "2026-10-04T15:00:00-05:00", "naicsCode": "236220", "active": "Yes",
       "description": "https://api.sam.gov/prod/opportunities/v1/noticedesc?noticeid=5b345bbb7127b91a3ad577b203fc6f68",
       "uiLink": "https://sam.gov/opp/5b345bbb7127b91a3ad577b203fc6f68/view"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "SAM-KEY-123456"}, 50, "test")
    return build_server(SPEC, transport=t)


def _mmddyyyy(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%m/%d/%Y")


@pytest.mark.asyncio
async def test_tools_are_search_and_get():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search_postings"]


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_the_mandatory_mm_dd_yyyy_window_and_maps_fields():
    route = respx.get(url__startswith=API).mock(return_value=httpx.Response(200, json={"totalRecords": 34, "limit": 25, "offset": 1, "opportunitiesData": [OPP], "links": []}))
    res = await _server().call_tool("search_postings", {"query": "renovation", "category": "236220", "page": 2})
    assert res.is_error is False, res.structured_content
    p = res.structured_content["postings"][0]
    assert p["id"] == OPP["noticeId"] and p["title"] == OPP["title"] and p["buyer"] == OPP["fullParentPathName"]
    assert p["url"] == OPP["uiLink"] and p["posted_at"] == "2026-09-04" and p["deadline"] == "2026-10-04T15:00:00-05:00"
    assert res.structured_content["total"] == 34
    q = route.calls.last.request.url.params
    assert q["api_key"] == "SAM-KEY-123456" and q["title"] == "renovation" and q["ncode"] == "236220"
    assert q["postedTo"] == _mmddyyyy(0) and q["postedFrom"] == _mmddyyyy(364)  # zero-padded, within one year
    assert q["limit"] == "25" and q["offset"] == "1"  # offset is the zero-based page index


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_filters_by_noticeid():
    route = respx.get(url__startswith=API).mock(return_value=httpx.Response(200, json={"totalRecords": 1, "opportunitiesData": [OPP]}))
    res = await _server().call_tool("get_posting", {"id": OPP["noticeId"]})
    assert res.is_error is False and res.structured_content["id"] == OPP["noticeId"]
    q = route.calls.last.request.url.params
    assert q["noticeid"] == OPP["noticeId"] and q["limit"] == "1" and q["postedFrom"] == _mmddyyyy(364)


@pytest.mark.asyncio
@respx.mock
async def test_bad_key_and_unknown_notice_are_errors_without_leaking_the_key():
    respx.get(url__startswith=API).mock(side_effect=[
        httpx.Response(403, json={"error": {"code": "API_KEY_INVALID", "message": "An invalid api_key was supplied"}}),
        httpx.Response(200, json={"totalRecords": 0, "opportunitiesData": []})])
    res = await _server().call_tool("search_postings", {"query": "x"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and "SAM-KEY-123456" not in json.dumps(res.structured_content)
    res = await _server().call_tool("get_posting", {"id": "nope"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"
