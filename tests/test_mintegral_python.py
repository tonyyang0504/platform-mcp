import hashlib
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

SPEC = json.loads((ROOT / "catalog" / "ads" / "mintegral.json").read_text(encoding="utf-8"))
BASE = "https://ss-api.mintegral.com"
CREDS = {"access_key": "AK-mtg-1", "api_key": "APIKEY-mtg-secret"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_token_header_is_md5_of_key_and_md5_timestamp(monkeypatch):
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1790301600.0)
    route = respx.get(f"{BASE}/api/open/v1/account/balance").mock(return_value=httpx.Response(200, json={
        "code": 200, "msg": "success", "data": {"total": 1, "list": [{"user_id": 1, "username": "Mintegral", "currency": "CNY", "balance": 100000}]}}))
    res = await _server().call_tool("list_accounts", {})
    assert res.is_error is False
    acc = res.structured_content["accounts"][0]
    assert acc["id"] == "1" and acc["name"] == "Mintegral" and acc["currency"] == "CNY"
    h = route.calls.last.request.headers
    assert h["access-key"] == "AK-mtg-1" and h["timestamp"] == "1790301600"
    inner = hashlib.md5(b"1790301600").hexdigest()
    assert h["token"] == hashlib.md5(("APIKEY-mtg-secret" + inner).encode()).hexdigest()


@pytest.mark.asyncio
@respx.mock
async def test_offers_are_listed_as_campaigns_with_query_paging():
    route = respx.get(url__startswith=f"{BASE}/api/open/v1/offers").mock(return_value=httpx.Response(200, json={
        "msg": "success", "code": 200, "data": {"page": 2, "limit": 10, "total": 520, "list": [
            {"campaign_id": 111, "offer_id": 10010, "offer_name": "campaign_test_1", "status": "RUNNING", "currency": "CNY", "start_time": "2019-10-01", "end_time": "2019-11-02"}]}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "1", "status": "RUNNING", "page": 2, "limit": 10})
    c = res.structured_content["campaigns"][0]
    assert c["id"] == "10010" and c["name"] == "campaign_test_1" and c["status"] == "RUNNING"
    assert res.structured_content["total"] == 520
    q = route.calls.last.request.url.params
    assert q["page"] == "2" and q["limit"] == "10" and q["status"] == "RUNNING"


@pytest.mark.asyncio
@respx.mock
async def test_budget_and_status_writes():
    b = respx.put(f"{BASE}/api/open/v1/offer/budget").mock(return_value=httpx.Response(200, json={"msg": "success", "code": 200, "data": {}}))
    out = (await _server().call_tool("update_budget", {"campaign_id": "123", "daily_budget": 80})).structured_content
    assert out["status"] == "updated"
    assert json.loads(b.calls.last.request.content) == {"offer_id": 123, "budget": [{"country_code": "ALL", "daily_cap_type": "BUDGET", "daily_cap": 80, "total_budget": "OPEN"}]}
    s = respx.put(f"{BASE}/api/open/v1/offer/status").mock(return_value=httpx.Response(200, json={"msg": "success", "code": 200, "data": {}}))
    assert (await _server().call_tool("pause_resume", {"campaign_id": "123", "action": "pause"})).is_error is False
    assert json.loads(s.calls.last.request.content) == {"offer_id": 123, "status": "STOPPED"}


@pytest.mark.asyncio
@respx.mock
async def test_non_200_code_is_an_error_and_tools_listed():
    respx.put(f"{BASE}/api/open/v1/offer/budget").mock(return_value=httpx.Response(200, json={"code": 11423, "msg": "budget is error!", "data": {"daily_cap": "daily_cap cannot less than 50!"}}))
    res = await _server().call_tool("update_budget", {"campaign_id": "123", "daily_budget": 10})
    assert res.is_error is True and "budget is error" in res.content[0].text
    assert sorted(t.name for t in await _server().list_tools()) == ["list_accounts", "list_campaigns", "me", "pause_resume", "update_budget"]
