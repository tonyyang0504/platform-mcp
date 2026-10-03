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

SPEC = json.loads((ROOT / "catalog" / "deals" / "ted_eu.json").read_text(encoding="utf-8"))
URL = "https://api.ted.europa.eu/v3/notices/search"
FIELDS = ["publication-number", "notice-title", "publication-date", "buyer-name", "deadline-receipt-tender-date-lot", "links"]

# ExpertSearchResponse per api-v3.yaml; shapes as returned live on 2026-09-24 (i18n maps keyed by ISO 639-2, links per language)
NOTICE = {
    "publication-number": "412169-2016", "publication-date": "2016-11-23+01:00",
    "notice-title": {"eng": "Software licences and support", "spa": "Licencias de software y soporte"},
    "buyer-name": {"eng": ["Achilles South Europe, S.L.U."], "spa": ["Achilles South Europe, S.L.U."]},
    "deadline-receipt-tender-date-lot": ["2026-12-01+01:00"],
    "links": {"xml": {"MUL": "https://ted.europa.eu/en/notice/412169-2016/xml"}, "html": {"ENG": "https://ted.europa.eu/en/notice/-/detail/412169-2016", "SPA": "https://ted.europa.eu/es/notice/-/detail/412169-2016"}},
}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_search_is_offered():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search_postings"]
    assert tools[0].annotations.read_only_hint is True and tools[0].meta["platform_mcp/endpoint"] == "/v3/notices/search"
    assert "UNCONFIRMED" in SPEC["adapter"]["not_offered"]["get_posting"] and "submit_bid" in SPEC["adapter"]["not_offered"]


@pytest.mark.asyncio
@respx.mock
async def test_search_posts_the_typed_fields_array_and_maps_i18n_notices():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"notices": [NOTICE], "totalNoticeCount": 43059, "timedOut": False}))
    res = await _server().call_tool("search_postings", {"query": 'FT~"software"', "page": 2, "limit": 50})
    assert res.is_error is False
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == "412169-2016" and p["title"] == "Software licences and support" and p["buyer"] == "Achilles South Europe, S.L.U."
    assert p["url"] == "https://ted.europa.eu/en/notice/-/detail/412169-2016" and p["deadline"] == "2026-12-01+01:00" and p["posted_at"] == "2016-11-23+01:00"
    assert p["raw"]["notice-title"]["spa"].startswith("Licencias")
    assert sc["total"] == 43059 and sc["next_page"] is None  # one row < limit
    body = json.loads(route.calls.last.request.content)
    assert body == {"query": 'FT~"software"', "fields": FIELDS, "page": 2, "limit": 50, "scope": "ACTIVE", "paginationMode": "PAGE_NUMBER"}
    assert isinstance(body["fields"], list) and isinstance(body["limit"], int)


@pytest.mark.asyncio
@respx.mock
async def test_limit_is_capped_at_250_and_english_gaps_are_null():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"notices": [{**NOTICE, "notice-title": {"spa": "x"}, "buyer-name": {"spa": ["y"]}, "deadline-receipt-tender-date-lot": None}], "totalNoticeCount": 1}))
    res = await _server().call_tool("search_postings", {"query": 'notice-title~"software"', "limit": 100})
    assert res.is_error is False
    p = res.structured_content["postings"][0]
    assert p["title"] is None and p["buyer"] is None and p["deadline"] is None and p["id"] == "412169-2016"
    assert json.loads(route.calls.last.request.content)["limit"] == 100


@pytest.mark.asyncio
@respx.mock
async def test_query_syntax_error_is_an_is_error_result():
    # live answer for a plain-word query (opened 2026-09-24)
    respx.post(URL).mock(return_value=httpx.Response(400, json={"message": "Syntax error in expert query at line 1, col 8: mismatched input '<EOF>' expecting {NOT, IN, '!=', '=', '~', '!~', COMPARISON_OPERATOR}", "error": {"type": "QUERY_SYNTAX_ERROR"}}))
    res = await _server().call_tool("search_postings", {"query": "software"})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and "QUERY_SYNTAX_ERROR" in res.structured_content["message"]
