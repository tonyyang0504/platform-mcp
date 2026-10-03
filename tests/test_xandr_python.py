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

SPEC = json.loads((ROOT / "catalog" / "ads" / "xandr.json").read_text(encoding="utf-8"))
B = "https://api.appnexus.com"


def _server():
    creds = {"username": "api-user", "password": "PASSWORD-xd", "advertiser_id": "11"}
    return build_server(SPEC, transport=Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds, 50, "test"))


def _auth():
    return respx.post(f"{B}/auth").mock(return_value=httpx.Response(200, json={"response": {"status": "OK", "token": "h20hbtptiv3vlp1rkm3ve1qig0"}}))


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "list_accounts", "list_campaigns", "pause_resume"}


@pytest.mark.asyncio
@respx.mock
async def test_nested_auth_body_and_raw_token_header():
    auth = _auth()
    me = respx.get(url__startswith=f"{B}/user").mock(return_value=httpx.Response(200, json={"response": {"status": "OK", "user": {"id": 5, "username": "api-user"}}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False
    assert json.loads(auth.calls[0].request.content) == {"auth": {"username": "api-user", "password": "PASSWORD-xd"}}
    req = me.calls[0].request
    assert req.headers["Authorization"] == "h20hbtptiv3vlp1rkm3ve1qig0" and str(req.url) == f"{B}/user?current"


@pytest.mark.asyncio
@respx.mock
async def test_advertisers_and_line_items_paging():
    _auth()
    adv = respx.get(url__startswith=f"{B}/advertiser").mock(return_value=httpx.Response(200, json={"response": {"status": "OK", "count": 8, "advertisers": [{"id": 11, "name": "Acme", "default_currency": "USD"}]}}))
    li = respx.get(url__startswith=f"{B}/line-item").mock(return_value=httpx.Response(200, json={"response": {"status": "OK", "count": 1, "line-items": [
        {"id": 152083, "name": "LI 1", "state": "active", "currency": "USD", "start_date": None, "end_date": None}]}}))
    s = _server()
    a = await s.call_tool("list_accounts", {})
    assert a.structured_content["accounts"][0] == {**a.structured_content["accounts"][0], "id": "11", "currency": "USD"}
    assert adv.calls[0].request.url.params["start_element"] == "0" and adv.calls[0].request.url.params["num_elements"] == "100" and a.structured_content["total"] == 8
    c = await s.call_tool("list_campaigns", {"account_id": "11", "status": "active"})
    assert c.structured_content["campaigns"][0]["id"] == "152083"
    q = li.calls[0].request.url.params
    assert q["advertiser_id"] == "11" and q["state"] == "active" and q["start_element"] == "0"


@pytest.mark.asyncio
@respx.mock
async def test_pause_puts_line_item_state():
    _auth()
    route = respx.put(url__startswith=f"{B}/line-item").mock(return_value=httpx.Response(200, json={"response": {"status": "OK", "count": 1, "id": 152083, "line-item": {"id": 152083, "state": "inactive"}}}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "152083", "action": "pause"})
    assert res.is_error is False and res.structured_content["status"] == "updated"
    q = route.calls[0].request.url.params
    assert q["id"] == "152083" and q["advertiser_id"] == "11"
    assert json.loads(route.calls[0].request.content) == {"line-item": {"state": "inactive"}}


@pytest.mark.asyncio
@respx.mock
async def test_refused_login_is_auth_error_without_password():
    respx.post(f"{B}/auth").mock(return_value=httpx.Response(401, json={"response": {"error_id": "NOAUTH", "error": "bad password PASSWORD-xd"}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and "PASSWORD-xd" not in json.dumps(res.structured_content)
