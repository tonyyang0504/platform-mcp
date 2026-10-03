"""Lever Postings API: keyless list/get for one site (config site + api_host for global/EU)."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "lever.json").read_text(encoding="utf-8"))
POST = {"id": "681fbc53-1e34-4a46-8677-3a78118674eb", "text": "Approved Professional 3", "country": "US", "workplaceType": "remote",
        "categories": {"location": "Baltimore, MD", "team": "Operations", "allLocations": ["Baltimore, MD"]},
        "descriptionPlain": "Welcome to the Demo Job Listing", "hostedUrl": "https://jobs.lever.co/leverdemo/681fbc53-1e34-4a46-8677-3a78118674eb",
        "applyUrl": "https://jobs.lever.co/leverdemo/681fbc53-1e34-4a46-8677-3a78118674eb/apply", "createdAt": 1565990241800,
        "salaryRange": {"currency": "USD", "interval": "per-year-salary", "min": 90000, "max": 110000}}


def _server(host="api.lever.co"):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"site": "leverdemo", "api_host": host}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_and_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search"]
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_skip_limit_location_and_mode_json():
    respx.get("https://api.lever.co/v0/postings/leverdemo").mock(return_value=httpx.Response(200, json=[POST]))
    res = await _server().call_tool("search", {"query": "ops", "location": "Baltimore, MD", "page": 3, "limit": 10})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "681fbc53-1e34-4a46-8677-3a78118674eb" and p["title"] == "Approved Professional 3" and p["location"] == "Baltimore, MD"
    assert p["salary_min"] == 90000 and p["salary_max"] == 110000 and p["currency"] == "USD" and p["url"].startswith("https://jobs.lever.co/leverdemo/")
    params = respx.calls.last.request.url.params
    assert params["mode"] == "json" and params["skip"] == "20" and params["limit"] == "10" and params["location"] == "Baltimore, MD" and "query" not in params


@pytest.mark.asyncio
@respx.mock
async def test_eu_host_and_get_posting():
    respx.get("https://api.eu.lever.co/v0/postings/leverdemo/681fbc53-1e34-4a46-8677-3a78118674eb").mock(return_value=httpx.Response(200, json=POST))
    res = await _server("api.eu.lever.co").call_tool("get_posting", {"id": "681fbc53-1e34-4a46-8677-3a78118674eb"})
    assert res.is_error is False and res.structured_content["description"] == "Welcome to the Demo Job Listing"


@pytest.mark.asyncio
@respx.mock
async def test_unknown_posting_is_not_found():
    respx.get("https://api.lever.co/v0/postings/leverdemo/nope").mock(return_value=httpx.Response(404, json={"ok": False, "error": "Document not found"}))
    res = await _server().call_tool("get_posting", {"id": "nope"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"
