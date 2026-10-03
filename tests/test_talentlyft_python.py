"""TalentLyft Public Customer API: keyless /v2/public/{subdomain}/jobs with page/perPage/details."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "talentlyft.json").read_text(encoding="utf-8"))
URL = "https://api.talentlyft.com/v2/public/demo/jobs"
JOB = {"Id": 20532, "Title": "Creative Director", "ShortlinkUrl": "https://demo.talentlyft.com/o/gRnagN", "Department": "Creative",
       "Country": "United States", "City": "Portland", "Description": "<h2>Lead</h2>", "Requirements": None, "JobTags": []}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"subdomain": "demo"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_search_is_offered():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search"]
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "get_posting", "apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_pages_with_per_page_and_details_and_reads_count():
    respx.get(URL).mock(return_value=httpx.Response(200, json={"Results": [JOB], "Count": 2, "Page": 1, "PerPage": 1, "Pages": {"Next": f"{URL}?perPage=1&page=2"}}))
    res = await _server().call_tool("search", {"query": "director", "limit": 1})
    assert res.is_error is False
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == "20532" and p["title"] == "Creative Director" and p["location"] == "Portland" and p["url"].endswith("/o/gRnagN")
    assert p["description"] == "<h2>Lead</h2>" and p["raw"]["Country"] == "United States"
    assert sc["total"] == 2 and sc["next_page"] == 2
    assert dict(respx.calls.last.request.url.params) == {"page": "1", "perPage": "1", "details": "true"}


@pytest.mark.asyncio
@respx.mock
async def test_unknown_subdomain_is_not_found():
    respx.get(URL).mock(return_value=httpx.Response(404, json={"Message": "Not Found", "Errors": [], "ErrorCode": 30001}))
    res = await _server().call_tool("search", {"query": "x"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"
