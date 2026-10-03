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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "adzuna.json").read_text(encoding="utf-8"))
SEARCH = "https://api.adzuna.com/v1/api/jobs/gb/search/1"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"app_id": "ID", "app_key": "KEY"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["me", "search"]  # no details endpoint, no apply, no messaging
    search = next(t for t in tools if t.name == "search")
    assert search.annotations.read_only_hint is True and search.annotations.destructive_hint is False
    assert search.input_schema["required"] == ["query"] and search.input_schema["additionalProperties"] is False
    assert search.meta["platform_mcp/endpoint"] == "/jobs/{country}/search/{page}"
    assert "pinned to gb" in search.description


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_both_query_credentials_and_maps_documented_fields():
    respx.get(SEARCH).mock(return_value=httpx.Response(200, json={
        "results": [{"id": "4567890123", "title": "Python Developer", "description": "We are looking for a Python developer ...",
                     "created": "2026-09-01T10:15:00Z", "company": {"display_name": "Acme Ltd"},
                     "location": {"area": ["UK", "London"], "display_name": "London, UK"}, "latitude": 51.5, "longitude": -0.12,
                     "salary_min": 50000, "salary_max": 60000, "salary_is_predicted": "0",
                     "category": {"tag": "it-jobs", "label": "IT Jobs"}, "contract_type": "permanent", "contract_time": "full_time",
                     "redirect_url": "https://www.adzuna.co.uk/jobs/land/ad/4567890123"}],
        "count": 1, "mean": 55000}))
    res = await _server().call_tool("search", {"query": "python", "location": "London"})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "4567890123" and p["company"] == "Acme Ltd" and p["location"] == "London, UK"
    assert p["url"] == "https://www.adzuna.co.uk/jobs/land/ad/4567890123" and p["salary_min"] == 50000 and p["posted_at"] == "2026-09-01T10:15:00Z"
    assert p["raw"]["category"]["label"] == "IT Jobs"
    assert res.structured_content["total"] == 1 and res.structured_content["next_page"] is None
    req = respx.calls.last.request
    assert req.url.path == "/v1/api/jobs/gb/search/1"
    assert req.url.params["what"] == "python" and req.url.params["where"] == "London" and req.url.params["results_per_page"] == "25"
    assert req.url.params["app_id"] == "ID" and req.url.params["app_key"] == "KEY"
    assert "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_page_argument_lands_in_the_path():
    route = respx.get("https://api.adzuna.com/v1/api/jobs/gb/search/3").mock(return_value=httpx.Response(200, json={"results": [], "count": 0}))
    res = await _server().call_tool("search", {"query": "python", "page": 3})
    assert res.is_error is False and route.called and res.structured_content["postings"] == []


@pytest.mark.asyncio
@respx.mock
async def test_refused_credentials_are_an_auth_error_result():
    respx.get(SEARCH).mock(return_value=httpx.Response(401, json={"exception": "AUTH_FAIL", "display": "Authorisation failed"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
