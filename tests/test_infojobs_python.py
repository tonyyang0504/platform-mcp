"""Adapter tests for jobs/infojobs (respx-mocked; no network)."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "infojobs.json").read_text(encoding="utf-8"))
CREDS = {'client_id': 'ij-cid', 'client_secret': 'ij-SECRETvalue'}


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
    assert sorted(t.name for t in tools) == ['get_posting', 'search']
    for t in tools:
        assert t.input_schema["additionalProperties"] is False and t.title
        assert t.annotations.read_only_hint in (True, False)


@pytest.mark.asyncio
@respx.mock
async def test_main_search_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='GET', url__startswith='https://api.infojobs.net/api/9/offer').mock(return_value=httpx.Response(200, json={'currentPage': 2, 'pageSize': 20, 'totalResults': 35, 'offers': [{'id': 'abc123', 'title': 'Java dev', 'author': {'name': 'Acme SL'}, 'city': 'Madrid', 'link': 'https://www.infojobs.net/madrid/java/of-iabc123', 'published': '2026-09-20T10:00:00Z'}]}))
    res = await _server().call_tool('search', {'query': 'java', 'page': 2, 'limit': 20})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'postings.0.id': 'abc123', 'postings.0.company': 'Acme SL', 'postings.0.location': 'Madrid', 'total': 35}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://api.infojobs.net/api/9/offer'
    assert req.url.params.get('q') == 'java'
    assert req.url.params.get('page') == '2'
    assert req.url.params.get('maxResults') == '20'
    assert req.headers['Authorization'].startswith('Basic ')


@pytest.mark.asyncio
@respx.mock
async def test_extra_get_posting_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='GET', url__startswith='https://api.infojobs.net/api/7/offer/abc123').mock(return_value=httpx.Response(200, json={'id': 'abc123', 'title': 'Java dev', 'profile': {'name': 'Acme SL'}, 'city': 'Madrid', 'description': 'Full text', 'creationDate': '2026-09-01T00:00:00.000+0000'}))
    res = await _server().call_tool('get_posting', {'id': 'abc123'})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'company': 'Acme SL', 'description': 'Full text'}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://api.infojobs.net/api/7/offer/abc123'


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result_not_a_protocol_error():
    _mock_token()
    respx.route(method='GET', url__startswith='https://api.infojobs.net/api/9/offer').mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))
    res = await _server().call_tool('search', {'query': 'x'})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 30


@pytest.mark.asyncio
@respx.mock
async def test_auth_failure_is_reported_without_leaking_the_secret():
    _mock_token()
    respx.route(method='GET', url__startswith='https://api.infojobs.net/api/9/offer').mock(return_value=httpx.Response(401, json={"error": "bad credentials ij-SECRETvalue"}))
    res = await _server().call_tool('search', {'query': 'x'})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert 'ij-SECRETvalue' not in json.dumps(res.structured_content)
