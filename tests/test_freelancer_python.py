"""Adapter tests for deals/freelancer (respx-mocked; no network)."""
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

SPEC = json.loads((ROOT / "catalog" / "deals" / "freelancer.json").read_text(encoding="utf-8"))
CREDS = {'access_token': 'FL-TOKEN-secret', 'bidder_id': '4242', 'milestone_percentage': '50'}


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
    assert sorted(t.name for t in tools) == ['bid_status', 'get_posting', 'list_messages', 'me', 'search_postings', 'send_message', 'submit_bid', 'withdraw_bid']
    for t in tools:
        assert t.input_schema["additionalProperties"] is False and t.title
        assert t.annotations.read_only_hint in (True, False)


@pytest.mark.asyncio
@respx.mock
async def test_main_submit_bid_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='POST', url__startswith='https://www.freelancer.com/api/projects/0.1/bids/').mock(return_value=httpx.Response(200, json={'status': 'success', 'result': {'id': 9001, 'bidder_id': 4242, 'project_id': 101, 'award_status': None}}))
    res = await _server().call_tool('submit_bid', {'posting_id': '101', 'amount': 250.5, 'period_days': 7, 'message': 'Proposal'})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'bid_id': '9001', 'status': 'submitted'}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://www.freelancer.com/api/projects/0.1/bids/'
    assert req.headers['freelancer-oauth-v1'] == 'FL-TOKEN-secret'
    assert json.loads(req.content) == {'project_id': 101, 'bidder_id': 4242, 'amount': 250.5, 'period': 7, 'milestone_percentage': 50, 'description': 'Proposal'}


@pytest.mark.asyncio
@respx.mock
async def test_extra_withdraw_bid_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='PUT', url__startswith='https://www.freelancer.com/api/projects/0.1/bids/9001/').mock(return_value=httpx.Response(200, json={'status': 'success'}))
    res = await _server().call_tool('withdraw_bid', {'bid_id': '9001'})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'status': 'retracted'}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://www.freelancer.com/api/projects/0.1/bids/9001/'
    assert {k: v[0] for k, v in parse_qs(req.content.decode()).items()} == {'action': 'retract'}


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result_not_a_protocol_error():
    _mock_token()
    respx.route(method='GET', url__startswith='https://www.freelancer.com/api/projects/0.1/projects/active/').mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))
    res = await _server().call_tool('search_postings', {'query': 'x'})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 30


@pytest.mark.asyncio
@respx.mock
async def test_auth_failure_is_reported_without_leaking_the_secret():
    _mock_token()
    respx.route(method='GET', url__startswith='https://www.freelancer.com/api/projects/0.1/projects/active/').mock(return_value=httpx.Response(401, json={"error": "bad credentials FL-TOKEN-secret"}))
    res = await _server().call_tool('search_postings', {'query': 'x'})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert 'FL-TOKEN-secret' not in json.dumps(res.structured_content)
