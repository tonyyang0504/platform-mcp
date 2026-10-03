"""Adapter tests for jobs/hh_ru (respx-mocked; no network)."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "hh_ru.json").read_text(encoding="utf-8"))
CREDS = {'client_id': 'hh-cid', 'client_secret': 'hh-SECRETvalue', 'user_agent': 'MyApp/1.0 (dev@example.com)'}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope"))
    return build_server(SPEC, transport=t)


def _dig(obj, path):
    for part in path.split("."):
        obj = obj[int(part)] if isinstance(obj, list) else obj.get(part)
    return obj


def _mock_token():
    return respx.post('https://api.hh.ru/token').mock(return_value=httpx.Response(200, json={'access_token': 'HH-APP-TOKEN', 'token_type': 'bearer'}))


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ['get_posting', 'me', 'search']
    for t in tools:
        assert t.input_schema["additionalProperties"] is False and t.title
        assert t.annotations.read_only_hint in (True, False)


@pytest.mark.asyncio
@respx.mock
async def test_main_search_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='GET', url__startswith='https://api.hh.ru/vacancies').mock(return_value=httpx.Response(200, json={'items': [{'id': '93353083', 'name': 'Python developer', 'employer': {'name': 'Yandex'}, 'area': {'name': 'Москва'}, 'alternate_url': 'https://hh.ru/vacancy/93353083', 'published_at': '2026-09-20T10:00:00+0300', 'salary': {'from': 200000, 'to': 300000, 'currency': 'RUR', 'gross': False}, 'snippet': {'responsibility': 'Писать код'}}], 'found': 1234, 'page': 1, 'pages': 124, 'per_page': 10}))
    res = await _server().call_tool('search', {'query': 'python', 'page': 2, 'limit': 10})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'postings.0.id': '93353083', 'postings.0.company': 'Yandex', 'postings.0.salary_min': 200000, 'postings.0.currency': 'RUR', 'total': 1234, 'next_page': None}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://api.hh.ru/vacancies'
    assert req.url.params.get('text') == 'python'
    assert req.url.params.get('page') == '1'
    assert req.url.params.get('per_page') == '10'
    assert req.headers['Authorization'] == 'Bearer HH-APP-TOKEN'
    assert {k: v[0] for k, v in parse_qs(token.calls.last.request.content.decode()).items()} == {'grant_type': 'client_credentials', 'client_id': 'hh-cid', 'client_secret': 'hh-SECRETvalue'}


@pytest.mark.asyncio
@respx.mock
async def test_extra_me_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='GET', url__startswith='https://api.hh.ru/me').mock(return_value=httpx.Response(200, json={'auth_type': 'application'}))
    res = await _server().call_tool('me', {})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'ok': True, 'account.auth_type': 'application'}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://api.hh.ru/me'


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result_not_a_protocol_error():
    _mock_token()
    respx.route(method='GET', url__startswith='https://api.hh.ru/vacancies/1').mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))
    res = await _server().call_tool('get_posting', {'id': '1'})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 30


@pytest.mark.asyncio
@respx.mock
async def test_auth_failure_is_reported_without_leaking_the_secret():
    _mock_token()
    respx.route(method='GET', url__startswith='https://api.hh.ru/vacancies/1').mock(return_value=httpx.Response(401, json={"error": "bad credentials hh-SECRETvalue"}))
    res = await _server().call_tool('get_posting', {'id': '1'})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert 'hh-SECRETvalue' not in json.dumps(res.structured_content)
