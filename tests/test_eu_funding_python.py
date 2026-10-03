import json
import sys
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "deals" / "eu_funding.json").read_text(encoding="utf-8"))
URL = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
HIT = {"reference": "r1", "summary": "Fundamentals of Software Engineering (RIA)", "metadata": {
    "identifier": ["HORIZON-CL4-2024-DIGITAL-EMERGING-01-22"], "title": ["Fundamentals of Software Engineering (RIA)"], "status": ["31094502"], "type": ["1"],
    "startDate": ["2023-11-15T00:00:00.000+0000"], "deadlineDate": ["2024-03-19T17:00:00.000+0000"], "callTitle": ["Digital emerging"], "descriptionByte": ["<p>Expected outcome</p>"]}}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


def _parts(request):
    msg = BytesParser(policy=default).parsebytes(b"Content-Type: " + request.headers["content-type"].encode() + b"\r\n\r\n" + request.content)
    return {p.get_param("name", header="content-disposition"): (p.get_content_type(), p.get_payload(decode=True).decode()) for p in msg.iter_parts()}


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_the_filter_as_a_json_typed_part():
    route = respx.post(url__startswith=URL).mock(return_value=httpx.Response(200, json={"totalResults": 676, "pageNumber": 1, "pageSize": 25, "results": [HIT]}))
    res = await _server().call_tool("search_postings", {"query": "software", "page": 2, "limit": 10})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["id"] == "HORIZON-CL4-2024-DIGITAL-EMERGING-01-22" and p["deadline"].startswith("2024-03-19") and res.structured_content["total"] == 676
    req = route.calls[0].request
    assert dict(req.url.params) == {"apiKey": "SEDIA", "text": "software", "pageSize": "10", "pageNumber": "2"}
    parts = _parts(req)
    ctype, q = parts["query"]
    assert ctype == "application/json"
    must = json.loads(q)["bool"]["must"]
    assert must == [{"terms": {"type": ["0", "1", "2", "8"]}}, {"terms": {"status": ["31094501", "31094502"]}}]
    assert parts["languages"] == ("application/json", '["en"]')


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_quotes_the_identifier():
    route = respx.post(url__startswith=URL).mock(return_value=httpx.Response(200, json={"totalResults": 1, "results": [HIT]}))
    res = await _server().call_tool("get_posting", {"id": "HORIZON-CL4-2024-DIGITAL-EMERGING-01-22"})
    assert res.structured_content["title"] == "Fundamentals of Software Engineering (RIA)" and res.structured_content["description"] == "<p>Expected outcome</p>"
    assert route.calls[0].request.url.params["text"] == '"HORIZON-CL4-2024-DIGITAL-EMERGING-01-22"'
    assert "status" not in json.loads(_parts(route.calls[0].request)["query"][1])["bool"]["must"][0]["terms"]


@pytest.mark.asyncio
@respx.mock
async def test_unknown_identifier_is_not_found():
    # get_posting is a read verb sent as a POST search: an empty answer is not_found (forge stress test 2026-10;
    # it used to be invalid_input because the runtime judged reads by the HTTP method)
    respx.post(url__startswith=URL).mock(return_value=httpx.Response(200, json={"totalResults": 0, "results": []}))
    res = await _server().call_tool("get_posting", {"id": "NOPE"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"


@pytest.mark.asyncio
@respx.mock
async def test_probe_uses_inline_text_wildcard():
    route = respx.post(url__startswith=URL).mock(return_value=httpx.Response(200, json={"totalResults": 1225, "results": [HIT]}))
    assert (await _server().call_tool("me", {})).is_error is False
    assert route.calls[0].request.url.params["text"] == "***"
