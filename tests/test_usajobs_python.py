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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "usajobs.json").read_text(encoding="utf-8"))
SEARCH = "https://data.usajobs.gov/api/Search"
ITEM = {"MatchedObjectId": "812345600", "MatchedObjectDescriptor": {
    "PositionID": "DE-12345-26-ABC", "PositionTitle": "IT Specialist (APPSW)", "PositionURI": "https://www.usajobs.gov/job/812345600",
    "ApplyURI": ["https://www.usajobs.gov/job/812345600?PostingChannelID=RESTAPI"],
    "PositionLocation": [{"LocationName": "Washington, District of Columbia", "CountryCode": "United States"}],
    "PositionRemuneration": [{"MinimumRange": "99200.0", "MaximumRange": "128956.0", "RateIntervalCode": "PA"}],
    "QualificationSummary": "You must have one year of specialized experience ...",
    "UserArea": {"Details": {"JobSummary": "Serves as an IT Specialist ...", "TeleworkEligible": True}}}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "k", "email": "me@example.com"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "me", "search"]  # apply / messaging happen on usajobs.gov via login.gov
    search = next(t for t in tools if t.name == "search")
    assert search.annotations.read_only_hint is True and search.annotations.destructive_hint is False
    assert search.input_schema["required"] == ["query"] and search.meta["platform_mcp/docs"] == "https://developer.usajobs.gov/api-reference/get-api-search"


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_both_headers_and_maps_documented_fields():
    respx.get(SEARCH).mock(return_value=httpx.Response(200, json={"SearchResult": {"SearchResultCount": 1, "SearchResultItems": [ITEM]}}))
    res = await _server().call_tool("search", {"query": "python", "location": "Washington, DC", "page": 2, "limit": 50})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "DE-12345-26-ABC" and p["title"] == "IT Specialist (APPSW)" and p["location"] == "Washington, District of Columbia"
    assert p["url"] == "https://www.usajobs.gov/job/812345600" and p["description"].startswith("You must have")
    assert p["raw"]["MatchedObjectDescriptor"]["PositionRemuneration"][0]["MinimumRange"] == "99200.0"  # string amounts stay raw
    req = respx.calls.last.request
    assert req.headers["Authorization-Key"] == "k" and req.headers["User-Agent"] == "me@example.com" and req.headers["Host"] == "data.usajobs.gov"
    assert req.url.params["Keyword"] == "python" and req.url.params["LocationName"] == "Washington, DC"
    assert req.url.params["ResultsPerPage"] == "50" and req.url.params["Page"] == "2"


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_uses_the_position_id_search_parameter():
    respx.get(SEARCH).mock(return_value=httpx.Response(200, json={"SearchResult": {"SearchResultCount": 1, "SearchResultItems": [ITEM]}}))
    res = await _server().call_tool("get_posting", {"id": "DE-12345-26-ABC"})
    assert res.is_error is False and res.structured_content["id"] == "DE-12345-26-ABC" and res.structured_content["title"] == "IT Specialist (APPSW)"
    req = respx.calls.last.request
    assert req.url.params["PositionID"] == "DE-12345-26-ABC" and req.url.params["ResultsPerPage"] == "1"


@pytest.mark.asyncio
@respx.mock
async def test_refused_key_is_an_auth_error_result_without_the_secret():
    respx.get(SEARCH).mock(return_value=httpx.Response(401, text="Unauthorized"))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
