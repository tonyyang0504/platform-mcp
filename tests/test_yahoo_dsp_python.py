import json
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import jwt as pyjwt
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ads" / "yahoo_dsp.json").read_text(encoding="utf-8"))
CREDS = {"client_id": "197031e8-1546-410f", "client_secret": "SECRET-yahoo-dsp-0123456789abcdef0123"}
BASE = "https://dspapi.admanagerplus.yahoo.com"
TOKEN_URL = "https://id.b2b.yahooincapis.com/zts/v1/oauth2/token"


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope"))
    s = build_server(SPEC, transport=t)
    t.fixed_headers = a["headers"]
    return s


def _token():
    return respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "3f94eb47-a295", "scope": "api-client", "token_type": "Bearer", "expires_in": "599"}))


@pytest.mark.asyncio
@respx.mock
async def test_hs256_client_assertion_and_x_auth_headers():
    tok = _token()
    seats = respx.get(BASE + "/traffic/seats").mock(return_value=httpx.Response(200, json={"response": [{"id": 11, "name": "Seat"}], "errors": None}))
    assert (await _server().call_tool("me", {})).is_error is False
    form = {k: v[0] for k, v in parse_qs(tok.calls[0].request.content.decode()).items()}
    assert form["grant_type"] == "client_credentials" and form["scope"] == "api-client" and form["realm"] == "dsp"
    assert form["client_assertion_type"] == "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
    assert "client_id" not in form and "client_secret" not in form
    claims = pyjwt.decode(form["client_assertion"], CREDS["client_secret"], algorithms=["HS256"], audience="https://id.b2b.yahooincapis.com/zts/v1")
    assert claims["iss"] == claims["sub"] == "idb2b.dsp.dspapi.197031e8-1546-410f"
    assert 0 < claims["exp"] - claims["iat"] <= 3600 and claims["jti"]
    h = seats.calls[0].request.headers
    assert h["X-Auth-Token"] == "3f94eb47-a295" and h["X-Auth-Method"] == "OAuth2" and "Authorization" not in h


@pytest.mark.asyncio
@respx.mock
async def test_advertisers_and_campaigns():
    _token()
    respx.get(url__startswith=BASE + "/traffic/advertisers").mock(return_value=httpx.Response(200, json={"response": [{"id": 1, "name": "My Yahoo!!", "status": "ACTIVE", "currency": "USD"}], "errors": None}))
    camp = respx.get(url__startswith=BASE + "/traffic/campaigns").mock(return_value=httpx.Response(200, json={"response": [
        {"id": 735837, "name": "traffic test", "status": "ACTIVE", "budgetSchedules": [{"id": 745083, "scheduleBudget": 22.02, "scheduleDailyBudget": 6.12}]}], "errors": None}))
    s = _server()
    a = await s.call_tool("list_accounts", {})
    assert a.structured_content["accounts"][0]["id"] == "1"
    c = await s.call_tool("list_campaigns", {"account_id": "2034341", "page": 2, "limit": 10})
    assert c.structured_content["campaigns"][0]["daily_budget"] == 6.12 and c.structured_content["campaigns"][0]["id"] == "735837"
    assert dict(camp.calls[0].request.url.params) == {"accountId": "2034341", "page": "2", "limit": "10"}


@pytest.mark.asyncio
@respx.mock
async def test_pause_is_a_partial_put():
    _token()
    route = respx.put(BASE + "/traffic/campaigns/745085").mock(return_value=httpx.Response(200, json={"response": {"id": 745085, "status": "PAUSED"}, "errors": None}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "745085", "action": "pause"})
    assert res.structured_content["status"] == "PAUSED"
    assert json.loads(route.calls[0].request.content) == {"status": "PAUSED"}


@pytest.mark.asyncio
@respx.mock
async def test_refused_token_is_an_auth_error():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(401, json={"error": "invalid_client"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
