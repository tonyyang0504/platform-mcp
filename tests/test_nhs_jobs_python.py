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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "nhs_jobs.json").read_text(encoding="utf-8"))
URL = "https://www.jobs.nhs.uk/api/v1/search_xml"
VAC = ("<vacancyDetails><id>{id}</id><reference>{ref}</reference><title>Nurse</title><description>36 hours per week</description>"
       "<employer>InHealth Group</employer><type>Permanent</type><salary>Negotiable</salary><closeDate>2026-10-16</closeDate>"
       "<postDate>2026-09-18T14:04:51.822005681</postDate><url>https://beta.jobs.nhs.uk/candidate/jobadvert/{ref}</url>"
       "<locations><location>Bridgwater, BA11 5LA</location></locations></vacancyDetails>")


def _xml(*vacs):
    return ("<?xml version='1.0' encoding='UTF-8'?><nhsJobs>" + "".join(VAC.format(id=i, ref=r) for i, r in vacs)
            + "<totalPages>2665</totalPages><totalResults>5330</totalResults></nhsJobs>")


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_keyless_tools_follow_the_vocabulary():
    assert sorted(t.name for t in await _server().list_tools()) == ["get_posting", "search"]


@pytest.mark.asyncio
@respx.mock
async def test_search_parses_the_xml_feed():
    route = respx.get(URL).mock(return_value=httpx.Response(200, text=_xml((5609923, "M0035-26-0449"), (5596068, "A3233-26-0001")),
                                                             headers={"Content-Type": "application/xml"}))
    res = await _server().call_tool("search", {"query": "nurse", "page": 2, "limit": 2, "location": "Leeds"})
    assert res.is_error is False
    ps = res.structured_content["postings"]
    assert [p["id"] for p in ps] == ["M0035-26-0449", "A3233-26-0001"]
    assert ps[0]["company"] == "InHealth Group" and ps[0]["posted_at"].startswith("2026-09-18") and ps[0]["raw"]["salary"] == "Negotiable"
    q = route.calls.last.request.url.params
    assert q["keyword"] == "nurse" and q["page"] == "2" and q["limit"] == "2" and "location" not in q


@pytest.mark.asyncio
@respx.mock
async def test_single_vacancy_is_still_a_list():
    respx.get(URL).mock(return_value=httpx.Response(200, text=_xml((1, "X-1")), headers={"Content-Type": "application/xml"}))
    res = await _server().call_tool("search", {"query": "porter"})
    assert [p["id"] for p in res.structured_content["postings"]] == ["X-1"]


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_uses_the_job_reference():
    route = respx.get(URL).mock(return_value=httpx.Response(200, text=_xml((5596068, "A3233-26-0001")), headers={"Content-Type": "application/xml"}))
    res = await _server().call_tool("get_posting", {"id": "A3233-26-0001"})
    assert res.is_error is False and res.structured_content["url"].endswith("/A3233-26-0001")
    assert route.calls.last.request.url.params["jobReference"] == "A3233-26-0001"


@pytest.mark.asyncio
@respx.mock
async def test_server_error_is_an_is_error_result():
    respx.get(URL).mock(return_value=httpx.Response(502, text="Bad Gateway"))
    res = await _server().call_tool("search", {"query": "nurse"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
