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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "zalo.json").read_text(encoding="utf-8"))
CREDS = {"app_id": "4318123456", "secret_key": "ZALO-SECRET-abc", "refresh_token": "RT-zalo-1"}
TOKEN = "https://oauth.zaloapp.com/v4/oa/access_token"
API = "https://openapi.zalo.me"


def _server(creds=None):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], creds if creds is not None else dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _token():
    return respx.post(TOKEN).mock(return_value=httpx.Response(200, json={"access_token": "AT-zalo-1", "refresh_token": "RT-zalo-2", "expires_in": "90000"}))


@pytest.mark.asyncio
@respx.mock
async def test_refresh_grant_names_app_id_and_sends_secret_key_header():
    tok = _token()
    me = respx.get(API + "/v2.0/oa/getoa").mock(return_value=httpx.Response(200, json={"data": {"oaid": "446", "name": "Shop"}, "error": 0, "message": "Success"}))
    creds = dict(CREDS)
    res = await _server(creds).call_tool("me", {})
    assert res.is_error is False
    req = tok.calls[0].request
    assert parse_qs(req.content.decode()) == {"grant_type": ["refresh_token"], "refresh_token": ["RT-zalo-1"], "app_id": ["4318123456"]}
    assert req.headers["secret_key"] == "ZALO-SECRET-abc"
    assert me.calls[0].request.headers["access_token"] == "AT-zalo-1" and "Authorization" not in me.calls[0].request.headers
    assert creds["refresh_token"] == "RT-zalo-2"


@pytest.mark.asyncio
@respx.mock
async def test_list_inbound_and_get_thread_send_the_data_json():
    _token()
    rows = [{"src": 1, "time": 1619401853770, "type": "text", "message": "Chào shop", "message_id": "92e5", "from_id": "2512523625412515", "to_id": "3120036654733951760"}]
    route = respx.get(url__startswith=API + "/v2.0/oa/").mock(return_value=httpx.Response(200, json={"data": rows, "error": 0, "message": "Success"}))
    s = _server()
    r = await s.call_tool("list_inbound", {"page": 2, "limit": 5})
    m = r.structured_content["messages"][0]
    assert m["id"] == "92e5" and m["from"] == "2512523625412515" and m["text"] == "Chào shop"
    assert json.loads(route.calls[0].request.url.params["data"]) == {"offset": 5, "count": 5}
    await s.call_tool("get_thread", {"thread_id": "2512523625412515", "limit": 50})
    assert json.loads(route.calls[1].request.url.params["data"]) == {"user_id": "2512523625412515", "offset": 0, "count": 10}


@pytest.mark.asyncio
@respx.mock
async def test_send_consultation_text():
    _token()
    route = respx.post(API + "/v3.0/oa/message/cs").mock(return_value=httpx.Response(200, json={"data": {"message_id": "63ecf43f", "user_id": "2512", "sent_time": "1626926349402", "quota": {"quota_type": "reply"}}, "error": 0, "message": "Success"}))
    res = await _server().call_tool("send", {"to": "2512", "text": "hello, world!"})
    assert res.structured_content["message_id"] == "63ecf43f" and res.structured_content["status"] == "sent"
    assert json.loads(route.calls[0].request.content) == {"recipient": {"user_id": "2512"}, "message": {"text": "hello, world!"}}


@pytest.mark.asyncio
@respx.mock
async def test_error_code_is_an_auth_error_without_secrets():
    _token()
    respx.get(API + "/v2.0/oa/getoa").mock(return_value=httpx.Response(200, json={"error": -216, "message": "Access token is invalid"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "ZALO-SECRET-abc" not in json.dumps(res.structured_content)
