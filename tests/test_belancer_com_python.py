"""Adapter tests for deals/belancer_com (respx-mocked; no network)."""
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

SPEC = json.loads((ROOT / "catalog" / "deals" / "belancer_com.json").read_text(encoding="utf-8"))
CREDS = {'username': 'me@example.com', 'password': 'PASSWORDsecret'}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope"))
    return build_server(SPEC, transport=t)


def _dig(obj, path):
    for part in path.split("."):
        obj = obj[int(part)] if isinstance(obj, list) else obj.get(part)
    return obj


def _mock_token():
    return respx.post('https://belancer.com/api/auth/login').mock(return_value=httpx.Response(200, json={'access_token': 'BL-TOKEN-abc', 'token_type': 'bearer', 'user_id': 1, 'role': 'seller', 'expires_at': '2026-09-25T00:00:00Z'}))


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ['get_posting', 'me', 'search_postings']
    for t in tools:
        assert t.input_schema["additionalProperties"] is False and t.title
        assert t.annotations.read_only_hint in (True, False)


@pytest.mark.asyncio
@respx.mock
async def test_main_search_postings_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='GET', url__startswith='https://belancer.com/api/projects/search').mock(return_value=httpx.Response(200, json={'total': 205, 'page': 1, 'limit': 1, 'projects': [{'id': 380, 'name': 'Hire Broker', 'description': 'Need', 'currency': 'USD', 'min_budget': 8.0, 'max_budget': 30.0, 'created_at': '2026-09-23T15:23:11Z'}]}))
    res = await _server().call_tool('search_postings', {'query': 'logo', 'category': '553', 'min_budget': 10, 'page': 1, 'limit': 1})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'postings.0.id': '380', 'postings.0.budget_max': 30.0, 'total': 205, 'next_page': 2}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://belancer.com/api/projects/search'
    assert req.url.params.get('query') == 'logo'
    assert req.url.params.get('category_id') == '553'
    assert req.url.params.get('min_budget') == '10'
    assert req.url.params.get('page') == '1'
    assert req.url.params.get('limit') == '1'
    assert req.url.params.get('status') == 'open'
    assert req.headers['Authorization'] == 'Bearer BL-TOKEN-abc'
    assert json.loads(token.calls.last.request.content) == {'username': 'me@example.com', 'password': 'PASSWORDsecret'}


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result_not_a_protocol_error():
    _mock_token()
    respx.route(method='GET', url__startswith='https://belancer.com/api/projects/380').mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))
    res = await _server().call_tool('get_posting', {'id': '380'})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 30


@pytest.mark.asyncio
@respx.mock
async def test_auth_failure_is_reported_without_leaking_the_secret():
    _mock_token()
    respx.route(method='GET', url__startswith='https://belancer.com/api/projects/380').mock(return_value=httpx.Response(401, json={"error": "bad credentials PASSWORDsecret"}))
    res = await _server().call_tool('get_posting', {'id': '380'})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert 'PASSWORDsecret' not in json.dumps(res.structured_content)
