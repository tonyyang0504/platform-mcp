"""Adapter tests for deals/highergov (respx-mocked; no network)."""
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

SPEC = json.loads((ROOT / "catalog" / "deals" / "highergov.json").read_text(encoding="utf-8"))
CREDS = {'api_key': 'HG-KEY-secret123', 'search_id': 'S123'}


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
    route = respx.route(method='GET', url__startswith='https://www.highergov.com/api-external/opportunity/').mock(return_value=httpx.Response(200, json={'results': [{'opp_key': 'OPP1', 'title': 'Cloud migration', 'description_text': 'Text', 'agency': {'agency_name': 'GSA'}, 'posted_date': '2026-09-20', 'due_date': '2026-10-20', 'source_path': 'https://sam.gov/opp/1'}], 'meta': {'pagination': {'page': 2, 'pages': 9, 'count': 420}}}))
    res = await _server().call_tool('search_postings', {'page': 2, 'limit': 50})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'postings.0.id': 'OPP1', 'postings.0.buyer': 'GSA', 'postings.0.deadline': '2026-10-20', 'total': 420}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://www.highergov.com/api-external/opportunity/'
    assert req.url.params.get('api_key') == 'HG-KEY-secret123'
    assert req.url.params.get('search_id') == 'S123'
    assert req.url.params.get('page_number') == '2'
    assert req.url.params.get('page_size') == '50'


@pytest.mark.asyncio
@respx.mock
async def test_extra_get_posting_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='GET', url__startswith='https://www.highergov.com/api-external/opportunity/').mock(return_value=httpx.Response(200, json={'results': [{'opp_key': 'OPP1', 'title': 'Cloud migration'}], 'meta': {'pagination': {'count': 1}}}))
    res = await _server().call_tool('get_posting', {'id': 'OPP1'})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'id': 'OPP1', 'title': 'Cloud migration'}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://www.highergov.com/api-external/opportunity/'
    assert req.url.params.get('opp_key') == 'OPP1'


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result_not_a_protocol_error():
    _mock_token()
    respx.route(method='GET', url__startswith='https://www.highergov.com/api-external/opportunity/').mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))
    res = await _server().call_tool('search_postings', {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 30


@pytest.mark.asyncio
@respx.mock
async def test_auth_failure_is_reported_without_leaking_the_secret():
    _mock_token()
    respx.route(method='GET', url__startswith='https://www.highergov.com/api-external/opportunity/').mock(return_value=httpx.Response(401, json={"error": "bad credentials HG-KEY-secret123"}))
    res = await _server().call_tool('search_postings', {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert 'HG-KEY-secret123' not in json.dumps(res.structured_content)
