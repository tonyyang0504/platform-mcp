"""Adapter tests for deals/freelancehunt (respx-mocked; no network)."""
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

SPEC = json.loads((ROOT / "catalog" / "deals" / "freelancehunt.json").read_text(encoding="utf-8"))
CREDS = {'token': 'FH-TOKEN-secret', 'safe_type': 'split'}


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
    assert sorted(t.name for t in tools) == ['get_posting', 'list_messages', 'me', 'search_postings', 'send_message']
    for t in tools:
        assert t.input_schema["additionalProperties"] is False and t.title
        assert t.annotations.read_only_hint in (True, False)


@pytest.mark.asyncio
@respx.mock
async def test_main_search_postings_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='GET', url__startswith='https://api.freelancehunt.com/v2/projects').mock(return_value=httpx.Response(200, json={'data': [{'id': 299165, 'type': 'project', 'attributes': {'name': 'Full stack', 'description': 'PHP', 'budget': {'amount': 2300, 'currency': 'UAH'}, 'employer': {'login': 'hello-world'}, 'published_at': '2019-03-25T19:51:53+02:00', 'expired_at': '2019-04-01T16:51:53+03:00'}, 'links': {'self': {'web': 'https://freelancehunt.com/project/x/299165.html'}}}]}))
    res = await _server().call_tool('search_postings', {'category': '56,69', 'page': 2})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'postings.0.id': '299165', 'postings.0.buyer': 'hello-world', 'postings.0.budget_max': 2300, 'postings.0.currency': 'UAH', 'postings.0.url': 'https://freelancehunt.com/project/x/299165.html'}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://api.freelancehunt.com/v2/projects'
    assert req.url.params.get('page[number]') == '2'
    assert req.url.params.get('filter[skill_id]') == '56,69'
    assert req.headers['Authorization'] == 'Bearer FH-TOKEN-secret'


def test_submit_bid_is_not_offered_after_the_v2_deprecation():
    """Auth audit 2026-09-26: POST /v2/projects/{id}/bids answers 410 'This public endpoint is no longer available due to API v2 deprecation.'"""
    a = SPEC["adapter"]
    assert "submit_bid" not in a["tools"]
    assert "410" in a["not_offered"]["submit_bid"] and "deprecation" in a["not_offered"]["submit_bid"]


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result_not_a_protocol_error():
    _mock_token()
    respx.route(method='GET', url__startswith='https://api.freelancehunt.com/v2/projects/1').mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))
    res = await _server().call_tool('get_posting', {'id': '1'})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 30


@pytest.mark.asyncio
@respx.mock
async def test_auth_failure_is_reported_without_leaking_the_secret():
    _mock_token()
    respx.route(method='GET', url__startswith='https://api.freelancehunt.com/v2/projects/1').mock(return_value=httpx.Response(401, json={"error": "bad credentials FH-TOKEN-secret"}))
    res = await _server().call_tool('get_posting', {'id': '1'})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert 'FH-TOKEN-secret' not in json.dumps(res.structured_content)
