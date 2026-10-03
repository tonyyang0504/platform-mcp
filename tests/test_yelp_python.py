import base64
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

SPEC = json.loads((ROOT / "catalog" / "ads" / "yelp.json").read_text(encoding="utf-8"))
API = "https://partner-api.yelp.com"
CREDS = {"username": "partner-user", "password": "PASSWORDsecret1"}
PROGRAM = {"program_type": "CPC", "program_id": "hTF5yeJ8OUQim6AXrz8w", "program_status": "ACTIVE", "start_date": "2015-12-10",
           "end_date": "9999-12-31", "program_pause_status": "NOT_PAUSED",
           "program_metrics": {"currency": "USD", "budget": 10000, "ad_cost": 0}, "businesses": [{"yelp_business_id": "nR5LcSr2yPjpHKc_o2zQ"}]}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], CREDS, 50, "test"))


@pytest.mark.asyncio
@respx.mock
async def test_tools_and_probe_uses_basic_auth():
    route = respx.get(f"{API}/programs/v1").mock(return_value=httpx.Response(200, json={"total": 1, "payment_programs": [PROGRAM]}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["list_campaigns", "me", "pause_resume"]
    res = await server.call_tool("me", {})
    assert res.structured_content["ok"] is True
    req = route.calls.last.request
    assert req.headers["authorization"] == "Basic " + base64.b64encode(b"partner-user:PASSWORDsecret1").decode()
    assert req.url.params["limit"] == "1"


@pytest.mark.asyncio
@respx.mock
async def test_list_campaigns_offset_status_and_fields():
    route = respx.get(f"{API}/programs/v1").mock(return_value=httpx.Response(200, json={"total": 45, "offset": 20, "limit": 20, "payment_programs": [PROGRAM]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "ignored", "status": "paused", "page": 2, "limit": 20})
    out = res.structured_content
    c = out["campaigns"][0]
    assert c["id"] == "hTF5yeJ8OUQim6AXrz8w" and c["name"] == "CPC" and c["budget"] == 10000 and c["currency"] == "USD"
    assert c["start"] == "2015-12-10" and out["total"] == 45
    q = route.calls.last.request.url.params
    assert q["offset"] == "20" and q["limit"] == "20" and q["program_status"] == "PAUSED"
    assert "account_id" not in q


@pytest.mark.asyncio
@respx.mock
async def test_limit_capped_and_bad_status():
    route = respx.get(f"{API}/programs/v1").mock(return_value=httpx.Response(200, json={"total": 0, "payment_programs": []}))
    res = await _server().call_tool("list_campaigns", {"account_id": "x", "limit": 100})
    assert res.structured_content["campaigns"] == []
    assert route.calls.last.request.url.params["limit"] == "40" and "program_status" not in route.calls.last.request.url.params
    bad = await _server().call_tool("list_campaigns", {"account_id": "x", "status": "live"})
    assert bad.is_error is True


@pytest.mark.asyncio
@respx.mock
async def test_pause_resume_paths_and_errors():
    pause = respx.post(f"{API}/program/c6HT44PKCaXqzN_BdgKPCw/pause/v1").mock(return_value=httpx.Response(202))
    resume = respx.post(f"{API}/program/c6HT44PKCaXqzN_BdgKPCw/resume/v1").mock(return_value=httpx.Response(202))
    res = await _server().call_tool("pause_resume", {"campaign_id": "c6HT44PKCaXqzN_BdgKPCw", "action": "pause"})
    assert res.structured_content["status"] == "accepted" and pause.called
    res = await _server().call_tool("pause_resume", {"campaign_id": "c6HT44PKCaXqzN_BdgKPCw", "action": "resume"})
    assert res.is_error is False and resume.called
    respx.post(f"{API}/program/zzz/pause/v1").mock(return_value=httpx.Response(401, json={"error": {"id": "UNAUTHORIZED"}}))
    err = await _server().call_tool("pause_resume", {"campaign_id": "zzz", "action": "pause"})
    assert err.is_error is True
