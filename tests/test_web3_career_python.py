"""Adapter tests for jobs/web3_career (respx-mocked; no network)."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "web3_career.json").read_text(encoding="utf-8"))
CREDS = {'token': 'W3-TOKEN-secret'}


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
    route = respx.route(method='GET', url__startswith='https://web3.career/api/v1').mock(return_value=httpx.Response(200, json=['meta', 'v1', [{'id': '123', 'title': 'Solidity engineer', 'company': 'Uniswap', 'location': 'Remote', 'apply_url': 'https://web3.career/solidity-engineer-uniswap/123?utm_source=api', 'postedAt': '2026-09-20', 'description': '<p>x</p>'}]]))
    res = await _server().call_tool('search', {'query': 'solidity', 'limit': 5})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'postings.0.id': '123', 'postings.0.company': 'Uniswap', 'postings.0.url': 'https://web3.career/solidity-engineer-uniswap/123?utm_source=api'}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://web3.career/api/v1'
    assert req.url.params.get('tag') == 'solidity'
    assert req.url.params.get('limit') == '5'
    assert req.url.params.get('token') == 'W3-TOKEN-secret'


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result_not_a_protocol_error():
    _mock_token()
    respx.route(method='GET', url__startswith='https://web3.career/api/v1').mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))
    res = await _server().call_tool('search', {'query': 'rust'})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 30


@pytest.mark.asyncio
@respx.mock
async def test_auth_failure_is_reported_without_leaking_the_secret():
    _mock_token()
    respx.route(method='GET', url__startswith='https://web3.career/api/v1').mock(return_value=httpx.Response(401, json={"error": "bad credentials W3-TOKEN-secret"}))
    res = await _server().call_tool('search', {'query': 'rust'})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert 'W3-TOKEN-secret' not in json.dumps(res.structured_content)
