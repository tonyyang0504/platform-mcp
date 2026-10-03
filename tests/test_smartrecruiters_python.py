"""SmartRecruiters public Posting API: keyless q/city/country/limit/offset search and posting details for one company."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "smartrecruiters.json").read_text(encoding="utf-8"))
BASE = "https://api.smartrecruiters.com/v1/companies/smartrecruiters/postings"
ROW = {"id": "744000148454651", "name": "Data Operations Consultant", "uuid": "f4a3d5b9-5fa9-48af-ba55-30669c9c3e81", "company": {"identifier": "smartrecruiters", "name": "SmartRecruiters Inc"},
       "releasedDate": "2026-09-09T09:43:26.403Z", "location": {"city": "Krakow", "country": "pl", "remote": True, "fullLocation": "Krakow, Poland"},
       "typeOfEmployment": {"id": "contract", "label": "Contract"}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"company_identifier": "smartrecruiters"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_and_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search"]
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_q_city_country_and_offset_paging():
    respx.get(BASE).mock(return_value=httpx.Response(200, json={"offset": 20, "limit": 10, "totalFound": 57, "content": [ROW]}))
    res = await _server().call_tool("search", {"query": "data", "location": "Krakow", "country": "pl", "page": 3, "limit": 10})
    assert res.is_error is False
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == "744000148454651" and p["title"] == "Data Operations Consultant" and p["company"] == "SmartRecruiters Inc"
    assert p["location"] == "Krakow, Poland" and p["posted_at"].startswith("2026-09-09") and p["raw"]["typeOfEmployment"]["label"] == "Contract"
    assert sc["total"] == 57
    params = respx.calls.last.request.url.params
    assert params["q"] == "data" and params["city"] == "Krakow" and params["country"] == "pl" and params["limit"] == "10" and params["offset"] == "20"


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_reads_the_job_ad_description_and_url():
    body = {**ROW, "postingUrl": "https://jobs.smartrecruiters.com/smartrecruiters/744000148454651-data-operations-consultant",
            "jobAd": {"sections": {"jobDescription": {"title": "Job Description", "text": "<p>Do data ops</p>"}}}}
    respx.get(f"{BASE}/744000148454651").mock(return_value=httpx.Response(200, json=body))
    res = await _server().call_tool("get_posting", {"id": "744000148454651"})
    assert res.is_error is False
    assert res.structured_content["description"] == "<p>Do data ops</p>" and res.structured_content["url"].endswith("-data-operations-consultant")


@pytest.mark.asyncio
@respx.mock
async def test_unknown_posting_is_not_found():
    respx.get(f"{BASE}/1").mock(return_value=httpx.Response(404, json={"message": "Posting not found"}))
    res = await _server().call_tool("get_posting", {"id": "1"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"
