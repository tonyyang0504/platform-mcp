"""4dayweek.io: no-auth /api/v2/jobs (q, country, page, limit) and /api/v2/jobs/{slug}; 60 req/min with Retry-After."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "fourdayweek.json").read_text(encoding="utf-8"))
BASE = "https://4dayweek.io/api/v2/jobs"
JOB = {"id": "01a0d375-6596-792f-b378-c7980684ede8", "slug": "cloud-engineer-tech-lead-at-luscii-62e771ef", "title": "Cloud Engineer (Tech Lead)", "description": "At Luscii ...",
       "url": "https://4dayweek.io/job/cloud-engineer-tech-lead-at-luscii-62e771ef", "schedule_type": "4_day_week", "work_arrangement": "remote",
       "locations": [{"city": "Utrecht", "country": "Netherlands", "continent": "Europe", "work_arrangement": "remote", "is_primary": True}],
       "salary_min": 678200, "salary_max": 722200, "salary_currency": "EUR", "salary_period": "month", "posted_at": "2026-09-24T12:48:01Z",
       "company": {"id": "019b77eb", "slug": "luscii", "name": "Luscii", "url": "https://4dayweek.io/company/luscii"}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search"]
    search = next(t for t in tools if t.name == "search")
    assert search.annotations.read_only_hint is True and search.annotations.destructive_hint is False
    assert search.input_schema["required"] == ["query"] and search.meta["platform_mcp/docs"] == "https://4dayweek.io/developers"
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_q_country_page_limit_and_the_cent_salaries():
    respx.get(BASE).mock(return_value=httpx.Response(200, json={"data": [JOB], "page": 1, "limit": 1, "total": 15150, "has_more": True}))
    res = await _server().call_tool("search", {"query": "engineer", "location": "Netherlands", "limit": 1})
    assert res.is_error is False
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == "cloud-engineer-tech-lead-at-luscii-62e771ef" and p["title"] == "Cloud Engineer (Tech Lead)" and p["company"] == "Luscii"
    assert p["location"] == "Netherlands" and p["url"].endswith("-62e771ef") and p["posted_at"] == "2026-09-24T12:48:01Z"
    assert p["salary_min"] == 678200 and p["salary_max"] == 722200 and p["currency"] == "EUR" and p["raw"]["salary_period"] == "month"
    assert sc["total"] == 15150 and sc["next_page"] == 2
    req = respx.calls.last.request
    assert req.url.params["q"] == "engineer" and req.url.params["country"] == "Netherlands" and req.url.params["page"] == "1" and req.url.params["limit"] == "1"
    assert "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_reads_the_slug_endpoint_which_returns_the_job_directly():
    respx.get(f"{BASE}/cloud-engineer-tech-lead-at-luscii-62e771ef").mock(return_value=httpx.Response(200, json=JOB))
    res = await _server().call_tool("get_posting", {"id": "cloud-engineer-tech-lead-at-luscii-62e771ef"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "cloud-engineer-tech-lead-at-luscii-62e771ef" and sc["title"] == "Cloud Engineer (Tech Lead)" and sc["description"] == "At Luscii ..."
    assert sc["company"] == "Luscii" and sc["raw"]["work_arrangement"] == "remote"


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_and_unknown_slug_are_is_error_results():
    respx.get(BASE).mock(return_value=httpx.Response(429, headers={"Retry-After": "12"}))
    res = await _server().call_tool("search", {"query": "python"})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 12
    respx.get(f"{BASE}/nope").mock(return_value=httpx.Response(404, json={"error": "not found"}))
    res = await _server().call_tool("get_posting", {"id": "nope"})
    assert res.is_error is True and res.structured_content["error"] == "not_found" and res.structured_content["http_status"] == 404
