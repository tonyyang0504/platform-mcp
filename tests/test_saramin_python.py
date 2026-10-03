"""Adapter tests for jobs/saramin (respx-mocked; no network)."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "saramin.json").read_text(encoding="utf-8"))
CREDS = {'access_key': 'SR-KEY-secret123'}


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
    assert sorted(t.name for t in tools) == ['search']
    for t in tools:
        assert t.input_schema["additionalProperties"] is False and t.title
        assert t.annotations.read_only_hint in (True, False)


@pytest.mark.asyncio
@respx.mock
async def test_main_search_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='GET', url__startswith='https://oapi.saramin.co.kr/job-search').mock(return_value=httpx.Response(200, json={'jobs': {'count': 1, 'start': 1, 'total': '7629', 'job': [{'url': 'http://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=27614114', 'active': 1, 'company': {'detail': {'href': 'http://x', 'name': '(주)사람인'}}, 'position': {'title': '사무보조', 'location': {'code': '101050', 'name': '서울 > 관악구'}}, 'id': '27614114', 'posting-date': '2019-05-30T13:46:04+0900'}]}}))
    res = await _server().call_tool('search', {'query': '웹 퍼블리셔', 'page': 2, 'limit': 20})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'postings.0.id': '27614114', 'postings.0.company': '(주)사람인', 'postings.0.location': '서울 > 관악구', 'postings.0.posted_at': '2019-05-30T13:46:04+0900', 'total': None}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://oapi.saramin.co.kr/job-search'
    assert req.url.params.get('keywords') == '웹 퍼블리셔'
    assert req.url.params.get('start') == '1'
    assert req.url.params.get('count') == '20'
    assert req.url.params.get('fields') == 'posting-date'
    assert req.url.params.get('access-key') == 'SR-KEY-secret123'


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result_not_a_protocol_error():
    _mock_token()
    respx.route(method='GET', url__startswith='https://oapi.saramin.co.kr/job-search').mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))
    res = await _server().call_tool('search', {'query': 'x'})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 30


@pytest.mark.asyncio
@respx.mock
async def test_auth_failure_is_reported_without_leaking_the_secret():
    _mock_token()
    respx.route(method='GET', url__startswith='https://oapi.saramin.co.kr/job-search').mock(return_value=httpx.Response(401, json={"error": "bad credentials SR-KEY-secret123"}))
    res = await _server().call_tool('search', {'query': 'x'})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert 'SR-KEY-secret123' not in json.dumps(res.structured_content)
