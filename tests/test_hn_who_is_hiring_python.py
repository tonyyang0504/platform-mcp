"""Adapter tests for jobs/hn_who_is_hiring (respx-mocked; no network)."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "hn_who_is_hiring.json").read_text(encoding="utf-8"))
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
    assert sorted(t.name for t in tools) == ['get_posting']
    for t in tools:
        assert t.input_schema["additionalProperties"] is False and t.title
        assert t.annotations.read_only_hint in (True, False)


@pytest.mark.asyncio
@respx.mock
async def test_main_get_posting_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='GET', url__startswith='https://hacker-news.firebaseio.com/v0/item/45000001.json').mock(return_value=httpx.Response(200, json={'id': 45000001, 'by': 'acme_hiring', 'text': 'Acme | Backend engineer | Remote', 'time': 1758700000, 'type': 'comment', 'parent': 45000000}))
    res = await _server().call_tool('get_posting', {'id': '45000001'})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'id': '45000001', 'company': 'acme_hiring', 'title': 'Acme | Backend engineer | Remote'}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://hacker-news.firebaseio.com/v0/item/45000001.json'


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result_not_a_protocol_error():
    _mock_token()
    respx.route(method='GET', url__startswith='https://hacker-news.firebaseio.com/v0/item/1.json').mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))
    res = await _server().call_tool('get_posting', {'id': '1'})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 30
