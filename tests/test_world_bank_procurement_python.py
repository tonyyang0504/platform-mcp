"""Adapter tests for deals/world_bank_procurement (respx-mocked; no network)."""
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "deals" / "world_bank_procurement.json").read_text(encoding="utf-8"))
CREDS = {}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope"))
    return build_server(SPEC, transport=t)


def _dig(obj, path):
    for part in path.split("."):
        obj = obj[int(part)] if isinstance(obj, list) else obj.get(part)
    return obj


def _mock_token():
    return None


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ['get_posting', 'search_postings']
    for t in tools:
        assert t.input_schema["additionalProperties"] is False and t.title
        assert t.annotations.read_only_hint in (True, False)


@pytest.mark.asyncio
@respx.mock
async def test_main_search_postings_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='GET', url__startswith='https://search.worldbank.org/api/v2/procnotices').mock(return_value=httpx.Response(200, json={'rows': 10, 'os': '20', 'total': '19211', 'procnotices': [{'id': 'OP00470638', 'notice_type': 'Contract Award', 'noticedate': '23-Sep-2026', 'project_name': 'Malawi Fiscal Governance', 'bid_description': 'Consultancy services', 'submission_date': '2026-09-23T00:00:00Z', 'notice_text': '<div>x</div>'}]}))
    res = await _server().call_tool('search_postings', {'query': 'software', 'page': 3, 'limit': 10})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'postings.0.id': 'OP00470638', 'postings.0.buyer': 'Malawi Fiscal Governance', 'postings.0.title': 'Consultancy services', 'total': None}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://search.worldbank.org/api/v2/procnotices'
    assert req.url.params.get('qterm') == 'software'
    assert req.url.params.get('rows') == '10'
    assert req.url.params.get('os') == '20'
    assert req.url.params.get('format') == 'json'


@pytest.mark.asyncio
@respx.mock
async def test_extra_get_posting_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='GET', url__startswith='https://search.worldbank.org/api/v2/procnotices').mock(return_value=httpx.Response(200, json={'procnotices': [{'id': 'OP00470638', 'bid_description': 'Consultancy services'}]}))
    res = await _server().call_tool('get_posting', {'id': 'OP00470638'})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'id': 'OP00470638'}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://search.worldbank.org/api/v2/procnotices'
    assert req.url.params.get('id') == 'OP00470638'


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result_not_a_protocol_error():
    _mock_token()
    respx.route(method='GET', url__startswith='https://search.worldbank.org/api/v2/procnotices').mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))
    res = await _server().call_tool('search_postings', {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 30
