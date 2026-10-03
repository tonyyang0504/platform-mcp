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

SPEC = json.loads((ROOT / "catalog" / "deals" / "trademe_nz.json").read_text(encoding="utf-8"))
API = "https://api.trademe.co.nz/v1"
CREDS = {"consumer_key": "4E0D082355116884742E5F33B8A199F411", "consumer_secret": "160FCF77971DC92A38596288DB071A8CA5"}
AUTH = "OAuth oauth_consumer_key=4E0D082355116884742E5F33B8A199F411, oauth_signature_method=PLAINTEXT, oauth_signature=160FCF77971DC92A38596288DB071A8CA5%26"
JOB = {"ListingId": 5012345678, "Title": "Senior Designer", "Company": "Acme Ltd", "ShortDescription": "Design things", "StartDate": "/Date(1790200000000)/",
       "EndDate": "/Date(1792800000000)/", "JobLocation": "Auckland", "JobType": "FT"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], CREDS, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_are_search_and_get():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search_postings"]


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_the_documented_plaintext_oauth_header():
    route = respx.get(url__startswith=API + "/Search/Jobs.json").mock(return_value=httpx.Response(200, json={"TotalCount": 120, "Page": 2, "PageSize": 25, "List": [JOB]}))
    res = await _server().call_tool("search_postings", {"query": "designer", "category": "5000", "page": 2, "limit": 50})
    assert res.is_error is False, res.structured_content
    p = res.structured_content["postings"][0]
    assert p["id"] == "5012345678" and p["title"] == "Senior Designer" and p["buyer"] == "Acme Ltd" and p["description"] == "Design things"
    assert p["raw"]["StartDate"] == "/Date(1790200000000)/" and res.structured_content["total"] == 120
    req = route.calls.last.request
    assert req.headers["Authorization"] == AUTH  # consumer key + '<consumer secret>&' (the '&' URL-encoded as %26)
    q = req.url.params
    assert q["search_string"] == "designer" and q["category"] == "5000" and q["page"] == "2" and q["rows"] == "25"  # rows capped at 25 without a member token
    assert not any(k.startswith("oauth") for k in q)


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_reads_listing_details():
    route = respx.get(API + "/Listings/5012345678.json").mock(return_value=httpx.Response(200, json={**JOB, "Body": "Full job description"}))
    res = await _server().call_tool("get_posting", {"id": "5012345678"})
    assert res.is_error is False and res.structured_content["description"] == "Full job description"
    assert route.calls.last.request.headers["Authorization"] == AUTH


@pytest.mark.asyncio
@respx.mock
async def test_rejected_signature_is_an_auth_error_without_the_secret():
    respx.get(url__startswith=API + "/Search/Jobs.json").mock(return_value=httpx.Response(401, json={"ErrorDescription": "Invalid signature 160FCF77971DC92A38596288DB071A8CA5"}))
    res = await _server().call_tool("search_postings", {"query": "x"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "160FCF77971DC92A38596288DB071A8CA5" not in json.dumps(res.structured_content)
