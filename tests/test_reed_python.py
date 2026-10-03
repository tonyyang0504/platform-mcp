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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "reed.json").read_text(encoding="utf-8"))


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "k"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    names = sorted(t.name for t in tools)
    assert names == ["get_posting", "me", "search"]  # apply / list_messages are not offered by Reed
    search = next(t for t in tools if t.name == "search")
    assert search.annotations.read_only_hint is True and search.annotations.destructive_hint is False
    assert search.input_schema["required"] == ["query"] and search.input_schema["additionalProperties"] is False
    assert search.output_schema["properties"]["postings"]["type"] == "array"
    assert search.title == "Search job postings"


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_documented_fields_and_pagination():
    respx.get("https://www.reed.co.uk/api/1.0/search").mock(return_value=httpx.Response(200, json={
        "results": [{"jobId": 1, "jobTitle": "Python dev", "employerName": "Acme", "locationName": "London", "jobUrl": "https://www.reed.co.uk/jobs/1", "date": "01/09/2026", "minimumSalary": 50000, "maximumSalary": 60000, "currency": "GBP", "jobDescription": "..."}],
        "totalResults": 1}))
    res = await _server().call_tool("search", {"query": "python", "location": "London"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["postings"][0]["id"] == "1" and sc["postings"][0]["company"] == "Acme" and sc["total"] == 1 and sc["next_page"] is None
    req = respx.calls.last.request
    assert req.url.params["keywords"] == "python" and req.url.params["resultsToTake"] == "25" and req.url.params["resultsToSkip"] == "0"
    assert req.headers["Authorization"].startswith("Basic ")


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result_not_a_protocol_error():
    respx.get("https://www.reed.co.uk/api/1.0/jobs/9").mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))
    res = await _server().call_tool("get_posting", {"id": "9"})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 30


@pytest.mark.asyncio
async def test_missing_argument_is_reported_as_a_tool_error():
    # the SDK validates arguments against the schema and reports the failure as an isError
    # result on the wire (SEP-1303); calling the server object directly surfaces the ToolError
    from mcp.server.mcpserver.exceptions import ToolError

    with pytest.raises(ToolError):
        await _server().call_tool("get_posting", {})
