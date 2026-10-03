import json
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "competitions" / "hackerone.json").read_text(encoding="utf-8"))

# https://api.hackerone.com/hacker-resources/ examples ("programs found", "Get Reports")
PROGRAM = {"id": 9, "type": "program", "attributes": {"handle": "acme", "name": "acme", "currency": "usd", "policy": "acme's program policy.",
           "submission_state": "open", "state": "public_mode", "started_accepting_at": None, "offers_bounties": True}}
REPORT = {"id": "3", "type": "report", "attributes": {"title": "XSS", "state": "new", "created_at": "2016-02-02T04:05:06.000Z"},
          "relationships": {"program": {"data": {"id": "5", "type": "program", "attributes": {"handle": "teamy"}}}}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_username": "hacker", "api_token": "h1-secret-token"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_and_not_offered():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["discover", "get_competition", "me", "my_entries"]
    assert set(SPEC["adapter"]["not_offered"]) == {"standings", "enter", "submit"}


@pytest.mark.asyncio
@respx.mock
async def test_discover_pages_programs_with_basic_auth():
    respx.get("https://api.hackerone.com/v1/hackers/programs").mock(return_value=httpx.Response(200, json={"data": [PROGRAM], "links": {}}))
    res = await _server().call_tool("discover", {"page": 2, "limit": 50})
    c = res.structured_content["competitions"][0]
    assert c["id"] == "acme" and c["status"] == "open" and c["raw"]["attributes"]["offers_bounties"] is True
    req = respx.calls.last.request
    assert req.url.params["page[number]"] == "2" and req.url.params["page[size]"] == "50"
    assert req.headers["Authorization"].startswith("Basic ")


@pytest.mark.asyncio
@respx.mock
async def test_program_detail_and_my_reports():
    respx.get("https://api.hackerone.com/v1/hackers/programs/acme").mock(return_value=httpx.Response(200, json={"data": PROGRAM}))
    res = await _server().call_tool("get_competition", {"competition_id": "acme"})
    assert res.structured_content["description"] == "acme's program policy."
    respx.get("https://api.hackerone.com/v1/hackers/me/reports").mock(return_value=httpx.Response(200, json={"data": [REPORT], "links": {}}))
    res = await _server().call_tool("my_entries", {})
    e = res.structured_content["entries"][0]
    assert e["id"] == "3" and e["competition_id"] == "teamy" and e["status"] == "new"


@pytest.mark.asyncio
@respx.mock
async def test_me_probe_and_rate_limit():
    respx.get("https://api.hackerone.com/v1/hackers/payments/balance").mock(return_value=httpx.Response(200, json={"data": {"balance": 105}}))
    res = await _server().call_tool("me", {})
    assert res.structured_content == {"ok": True, "account": {"data": {"balance": 105}}}
    respx.get("https://api.hackerone.com/v1/hackers/programs").mock(return_value=httpx.Response(429, headers={"Retry-After": "7"}))
    res = await _server().call_tool("discover", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 7
