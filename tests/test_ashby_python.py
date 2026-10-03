"""Ashby public Job Postings API: one organisation's board (config job_board_name), keyless, unpaged."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "ashby.json").read_text(encoding="utf-8"))
BOARD = "https://api.ashbyhq.com/posting-api/job-board/Ashby"
JOB = {"id": "7458d4e9-da2e-47bd-98cb-adfda43d42b2", "title": "Engineering Manager - EU", "department": "Engineering", "team": "EMEA Engineering",
       "employmentType": "FullTime", "location": "Remote - European Union", "publishedAt": "2024-03-04T14:29:08.532+00:00", "isListed": True,
       "isRemote": True, "workplaceType": "Remote", "jobUrl": "https://jobs.ashbyhq.com/Ashby/7458d4e9-da2e-47bd-98cb-adfda43d42b2",
       "applyUrl": "https://jobs.ashbyhq.com/Ashby/7458d4e9-da2e-47bd-98cb-adfda43d42b2/application", "descriptionHtml": "<p>Hi</p>", "descriptionPlain": "Hi",
       "compensation": {"compensationTierSummary": "€110K – €185K • Offers Equity"}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"job_board_name": "Ashby"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_search_is_offered_and_it_is_read_only():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search"]
    assert tools[0].annotations.read_only_hint is True and tools[0].annotations.destructive_hint is False
    assert tools[0].meta["platform_mcp/docs"] == "https://developers.ashbyhq.com/docs/public-job-posting-api"
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "get_posting", "apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_reads_the_configured_board_with_compensation_and_sends_no_query():
    respx.get(BOARD).mock(return_value=httpx.Response(200, json={"apiVersion": "1", "jobs": [JOB]}))
    res = await _server().call_tool("search", {"query": "manager", "location": "Berlin", "limit": 10})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "7458d4e9-da2e-47bd-98cb-adfda43d42b2" and p["title"] == "Engineering Manager - EU" and p["location"] == "Remote - European Union"
    assert p["url"].endswith("/7458d4e9-da2e-47bd-98cb-adfda43d42b2") and p["posted_at"].startswith("2024-03-04") and p["description"] == "Hi"
    assert p.get("company") is None and p["raw"]["compensation"]["compensationTierSummary"].startswith("€110K")
    assert res.structured_content["next_page"] is None
    params = dict(respx.calls.last.request.url.params)
    assert params == {"includeCompensation": "true"}


@pytest.mark.asyncio
@respx.mock
async def test_unknown_board_is_not_found():
    respx.get(BOARD).mock(return_value=httpx.Response(404, text="Not Found"))
    res = await _server().call_tool("search", {"query": "x"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"


@pytest.mark.asyncio
async def test_missing_board_name_is_an_auth_error_naming_the_variable(monkeypatch):
    monkeypatch.delenv("PLATFORM_MCP_ASHBY_JOB_BOARD_NAME", raising=False)
    res = await build_server(SPEC).call_tool("search", {"query": "x"})
    assert res.is_error is True and "PLATFORM_MCP_ASHBY_JOB_BOARD_NAME" in json.dumps(res.structured_content)
