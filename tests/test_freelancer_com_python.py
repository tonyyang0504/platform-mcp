"""Adapter tests for jobs/freelancer_com (respx-mocked; no network)."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "freelancer_com.json").read_text(encoding="utf-8"))
CREDS = {'access_token': 'FL-TOKEN-secret'}


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
    assert sorted(t.name for t in tools) == ['get_posting', 'list_messages', 'search']
    for t in tools:
        assert t.input_schema["additionalProperties"] is False and t.title
        assert t.annotations.read_only_hint in (True, False)


@pytest.mark.asyncio
@respx.mock
async def test_main_search_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='GET', url__startswith='https://www.freelancer.com/api/projects/0.1/projects/active/').mock(return_value=httpx.Response(200, json={'status': 'success', 'result': {'total_count': 57, 'projects': [{'id': 101, 'title': 'Build a scraper', 'description': 'Full', 'budget': {'minimum': 30, 'maximum': 250}, 'currency': {'code': 'USD'}, 'time_submitted': 1758700000}]}}))
    res = await _server().call_tool('search', {'query': 'python scraper', 'page': 3, 'limit': 10})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'postings.0.id': '101', 'postings.0.salary_max': 250, 'postings.0.currency': 'USD', 'total': 57}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://www.freelancer.com/api/projects/0.1/projects/active/'
    assert req.url.params.get('query') == 'python scraper'
    assert req.url.params.get('limit') == '10'
    assert req.url.params.get('offset') == '20'
    assert req.url.params.get('full_description') == 'true'
    assert req.headers['freelancer-oauth-v1'] == 'FL-TOKEN-secret'


@pytest.mark.asyncio
@respx.mock
async def test_extra_list_messages_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='GET', url__startswith='https://www.freelancer.com/api/messages/0.1/messages/').mock(return_value=httpx.Response(200, json={'status': 'success', 'result': {'messages': [{'id': 5, 'thread_id': 77, 'from_user': 9, 'message': 'hi', 'time_created': 1758700000}]}}))
    res = await _server().call_tool('list_messages', {'thread_id': '77'})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'messages.0.id': '5', 'messages.0.thread_id': '77', 'messages.0.text': 'hi'}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://www.freelancer.com/api/messages/0.1/messages/'
    assert req.url.params.get('threads[]') == '77'


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result_not_a_protocol_error():
    _mock_token()
    respx.route(method='GET', url__startswith='https://www.freelancer.com/api/projects/0.1/projects/101/').mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))
    res = await _server().call_tool('get_posting', {'id': '101'})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 30


@pytest.mark.asyncio
@respx.mock
async def test_auth_failure_is_reported_without_leaking_the_secret():
    _mock_token()
    respx.route(method='GET', url__startswith='https://www.freelancer.com/api/projects/0.1/projects/101/').mock(return_value=httpx.Response(401, json={"error": "bad credentials FL-TOKEN-secret"}))
    res = await _server().call_tool('get_posting', {'id': '101'})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert 'FL-TOKEN-secret' not in json.dumps(res.structured_content)
