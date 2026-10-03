"""Pinpoint public postings.json feed for one careers site (config company_subdomain)."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "pinpoint.json").read_text(encoding="utf-8"))
FEED = "https://workwithus.pinpointhq.com/postings.json"
POST = {"id": "559663", "title": "Founding Legal Counsel", "description": "<div>Hi</div>", "compensation_visible": True, "compensation_minimum": 90000,
        "compensation_maximum": 110000, "compensation_currency": "GBP", "compensation_frequency": "year", "employment_type": "full_time",
        "url": "https://workwithus.pinpointhq.com/en/postings/ce6c9e5c", "workplace_type": "remote", "location": {"id": "283", "name": "Remote", "city": "London"}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"company_subdomain": "workwithus"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_search_is_offered():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search"] and tools[0].annotations.read_only_hint is True
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "get_posting", "apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_hits_the_subdomain_feed_and_sends_location_as_city_state_name():
    respx.get(FEED).mock(return_value=httpx.Response(200, json={"data": [POST]}))
    res = await _server().call_tool("search", {"query": "legal", "location": "London", "page": 1, "limit": 5})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "559663" and p["title"] == "Founding Legal Counsel" and p["location"] == "Remote" and p["url"].endswith("ce6c9e5c")
    assert p["salary_min"] == 90000 and p["salary_max"] == 110000 and p["currency"] == "GBP" and p["raw"]["compensation_frequency"] == "year"
    assert dict(respx.calls.last.request.url.params) == {"location_city_state_name": "London"}


@pytest.mark.asyncio
@respx.mock
async def test_upstream_failure_is_an_is_error_result():
    respx.get(FEED).mock(return_value=httpx.Response(503, text="maintenance"))
    res = await _server().call_tool("search", {"query": "x"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
