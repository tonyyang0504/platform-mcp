import base64
import hashlib
import hmac
import json
import sys
from pathlib import Path
from urllib.parse import quote, unquote

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ads" / "x_ads.json").read_text(encoding="utf-8"))
BASE = "https://ads-api.x.com/12"
CREDS = {"consumer_key": "CK-x", "consumer_secret": "CS-x-secret", "access_token": "AT-x", "access_token_secret": "ATS-x-secret", "account_id": "18ce54d4x5t"}
enc = lambda s: quote(str(s), safe="-._~")  # noqa: E731


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _check_oauth(req, method):
    hdr = req.headers["Authorization"]
    assert hdr.startswith("OAuth ")
    oauth = {k: unquote(v.strip('"')) for k, v in (x.split("=", 1) for x in hdr[len("OAuth "):].split(", "))}
    sig = oauth.pop("oauth_signature")
    assert oauth["oauth_consumer_key"] == "CK-x" and oauth["oauth_token"] == "AT-x" and oauth["oauth_signature_method"] == "HMAC-SHA1"
    params = sorted([(enc(k), enc(v)) for k, v in req.url.params.multi_items()] + [(enc(k), enc(v)) for k, v in oauth.items()])
    url = str(req.url).split("?")[0]
    base = "&".join([method, enc(url), enc("&".join(f"{k}={v}" for k, v in params))])
    key = f"{enc('CS-x-secret')}&{enc('ATS-x-secret')}"
    assert sig == base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()


@pytest.mark.asyncio
@respx.mock
async def test_accounts_signed_with_oauth1_and_cursor():
    route = respx.get(url__startswith=f"{BASE}/accounts").mock(return_value=httpx.Response(200, json={
        "request": {"params": {}}, "next_cursor": "c-2", "data": [{"id": "18ce54d4x5t", "name": "API McTestface"}]}))
    res = await _server().call_tool("list_accounts", {})
    assert res.structured_content["accounts"][0]["id"] == "18ce54d4x5t" and res.structured_content["next_cursor"] == "c-2"
    req = route.calls.last.request
    assert req.url.params["count"] == "100"
    _check_oauth(req, "GET")


@pytest.mark.asyncio
@respx.mock
async def test_budget_put_in_micros_on_the_query_string():
    route = respx.put(url__startswith=f"{BASE}/accounts/18ce54d4x5t/campaigns/8wku2").mock(return_value=httpx.Response(200, json={
        "data": {"id": "8wku2", "daily_budget_amount_local_micro": 5500000, "entity_status": "PAUSED"}}))
    out = (await _server().call_tool("update_budget", {"campaign_id": "8wku2", "daily_budget": 5.5})).structured_content
    assert out["status"] == "updated"
    req = route.calls.last.request
    assert req.url.params["daily_budget_amount_local_micro"] == "5500000" and req.content == b""
    _check_oauth(req, "PUT")
    p = respx.put(url__startswith=f"{BASE}/accounts/18ce54d4x5t/campaigns/8wku2").mock(return_value=httpx.Response(200, json={"data": {"id": "8wku2"}}))
    assert (await _server().call_tool("pause_resume", {"campaign_id": "8wku2", "action": "pause"})).is_error is False
    assert p.calls.last.request.url.params["entity_status"] == "PAUSED"


@pytest.mark.asyncio
@respx.mock
async def test_campaigns_and_stats():
    respx.get(url__startswith=f"{BASE}/accounts/18ce54d4x5t/campaigns").mock(return_value=httpx.Response(200, json={
        "next_cursor": None, "data": [{"id": "8wku2", "name": "test", "entity_status": "PAUSED", "currency": "USD"}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "18ce54d4x5t"})
    assert res.structured_content["campaigns"][0] == {**res.structured_content["campaigns"][0], "id": "8wku2", "status": "PAUSED", "currency": "USD"}
    st = respx.get(url__startswith=f"{BASE}/stats/accounts/18ce54d4x5t").mock(return_value=httpx.Response(200, json={
        "data_type": "stats", "data": [{"id": "8wku2", "id_data": [{"segment": None, "metrics": {"impressions": [1233]}}]}]}))
    rep = await _server().call_tool("get_report", {"account_id": "18ce54d4x5t", "campaign_id": "8wku2", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert rep.is_error is False and rep.structured_content["rows"][0]["raw"]["id_data"][0]["metrics"]["impressions"] == [1233]
    q = st.calls.last.request.url.params
    assert q["entity"] == "CAMPAIGN" and q["entity_ids"] == "8wku2" and q["start_time"] == "2026-09-01" and q["granularity"] == "DAY"
