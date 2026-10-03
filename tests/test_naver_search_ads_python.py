import base64
import hashlib
import hmac
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ads" / "naver_search_ads.json").read_text(encoding="utf-8"))
B = "https://api.searchad.naver.com"
SECRET = "nv-secret-key-xyz"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "nv-license", "secret_key": SECRET, "customer_id": "1234567"}, 50, "test")
    return build_server(SPEC, transport=t)


def _expected_sig(req, method, path):
    ts = req.headers["X-Timestamp"]
    return base64.b64encode(hmac.new(SECRET.encode(), f"{ts}.{method}.{path}".encode(), hashlib.sha256).digest()).decode()


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "list_campaigns", "get_report", "update_budget", "pause_resume"}


@pytest.mark.asyncio
@respx.mock
async def test_list_campaigns_signed_headers():
    route = respx.get(f"{B}/ncc/campaigns").mock(return_value=httpx.Response(200, json=[
        {"nccCampaignId": "cmp-a001-01-000000000000001", "name": "브랜드", "status": "ELIGIBLE", "dailyBudget": 50000, "useDailyBudget": True, "userLock": False}]))
    res = await _server().call_tool("list_campaigns", {"account_id": "x", "limit": 50})
    assert res.is_error is False
    req = route.calls[0].request
    assert req.headers["X-API-KEY"] == "nv-license" and req.headers["X-Customer"] == "1234567"
    assert req.headers["X-Signature"] == _expected_sig(req, "GET", "/ncc/campaigns")
    assert parse_qs(urlparse(str(req.url)).query) == {"recordSize": ["50"]}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["budget"], c["status"]) == ("cmp-a001-01-000000000000001", 50000, "ELIGIBLE")


@pytest.mark.asyncio
@respx.mock
async def test_get_report_time_range_json_and_daily_rows():
    route = respx.get(f"{B}/stats").mock(return_value=httpx.Response(200, json={"data": [
        {"dateStart": "2026-09-01", "dateEnd": "2026-09-01", "impCnt": 900, "clkCnt": 30, "salesAmt": 15400, "ctr": 3.33, "cpc": 513, "ccnt": 2}], "summary": {}}))
    res = await _server().call_tool("get_report", {"account_id": "x", "campaign_id": "cmp-1", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    q = {k: v[0] for k, v in parse_qs(urlparse(str(route.calls[0].request.url)).query).items()}
    assert q["id"] == "cmp-1" and json.loads(q["timeRange"]) == {"since": "2026-09-01", "until": "2026-09-07"}
    assert json.loads(q["fields"]) == ["impCnt", "clkCnt", "salesAmt", "ctr", "cpc", "ccnt"] and q["timeIncrement"] == "1"
    assert route.calls[0].request.headers["X-Signature"] == _expected_sig(route.calls[0].request, "GET", "/stats")
    r = res.structured_content["rows"][0]
    assert (r["date"], r["spend"], r["clicks"]) == ("2026-09-01", 15400, 30)


@pytest.mark.asyncio
@respx.mock
async def test_update_budget_body_and_integer_guard():
    route = respx.put(f"{B}/ncc/campaigns/cmp-1").mock(return_value=httpx.Response(200, json={"nccCampaignId": "cmp-1", "dailyBudget": 70000, "useDailyBudget": True}))
    res = await _server().call_tool("update_budget", {"campaign_id": "cmp-1", "daily_budget": 70000})
    assert res.is_error is False and res.structured_content["status"] == "updated"
    req = route.calls[0].request
    assert parse_qs(urlparse(str(req.url)).query) == {"fields": ["budget"]}
    assert json.loads(req.content) == {"nccCampaignId": "cmp-1", "customerId": 1234567, "useDailyBudget": True, "dailyBudget": 70000}
    assert req.headers["X-Signature"] == _expected_sig(req, "PUT", "/ncc/campaigns/cmp-1")
    bad = await _server().call_tool("update_budget", {"campaign_id": "cmp-1", "daily_budget": 700.5})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_refused_signature_does_not_leak_secret():
    respx.get(f"{B}/billing/bizmoney").mock(return_value=httpx.Response(403, json={"title": "Invalid signature", "detail": SECRET}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and SECRET not in json.dumps(res.structured_content)


@pytest.mark.asyncio
@respx.mock
async def test_pause_resume_sets_user_lock_boolean_signed():
    route = respx.put(f"{B}/ncc/campaigns/cmp-1").mock(return_value=httpx.Response(200, json={"nccCampaignId": "cmp-1", "userLock": True}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "cmp-1", "action": "pause"})
    assert res.is_error is False and res.structured_content["status"] == "updated"
    req = route.calls[0].request
    assert parse_qs(urlparse(str(req.url)).query) == {"fields": ["userLock"]}
    assert json.loads(req.content) == {"nccCampaignId": "cmp-1", "customerId": 1234567, "userLock": True}
    assert req.headers["X-Signature"] == _expected_sig(req, "PUT", "/ncc/campaigns/cmp-1")
