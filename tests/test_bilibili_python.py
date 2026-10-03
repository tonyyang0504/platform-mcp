import hashlib
import hmac
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

SPEC = json.loads((ROOT / "catalog" / "social" / "bilibili.json").read_text(encoding="utf-8"))
CREDS = {"client_id": "93a0f774fae84e6c", "client_secret": "BILI-SECRET-0123", "refresh_token": "WxFDKwqScZIQ-1"}
TOKEN = "https://api.bilibili.com/x/account-oauth2/v1/refresh_token"
API = "https://member.bilibili.com/arcopen/fn"


def _server(creds=None):
    a = SPEC["adapter"]
    s = build_server(SPEC, transport=Transport(a["base_url"], a["auth"], creds if creds is not None else dict(CREDS), 50, "test", envelope=a.get("envelope")))
    return s


def _token():
    return respx.post(url__startswith=TOKEN).mock(return_value=httpx.Response(200, json={"code": 0, "message": "0", "data": {"access_token": "d30bedaa4d8e", "refresh_token": "WxFDKwqScZIQ-2", "expires_in": 1830220614}}))


def _check(request):
    h = request.headers
    assert h["x-bili-content-md5"] == hashlib.md5(request.content).hexdigest()
    payload = "\n".join(f"{k}:{h[k]}" for k in ["x-bili-accesskeyid", "x-bili-content-md5", "x-bili-signature-method", "x-bili-signature-nonce", "x-bili-signature-version", "x-bili-timestamp"])
    assert h["Authorization"] == hmac.new(CREDS["client_secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()
    assert h["x-bili-accesskeyid"] == CREDS["client_id"] and h["x-bili-signature-version"] == "2.0" and h["access-token"] == "d30bedaa4d8e"
    assert h["Content-Type"] == "application/json"


@pytest.mark.asyncio
@respx.mock
async def test_refresh_in_query_then_signed_get():
    tok = _token()
    me = respx.get(API + "/user/account/info").mock(return_value=httpx.Response(200, json={"code": 0, "message": "0", "data": {"name": "up主", "openid": "o1"}}))
    creds = dict(CREDS)
    res = await _server(creds).call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["data"]["openid"] == "o1"
    treq = tok.calls[0].request
    assert dict(treq.url.params) == {"client_id": CREDS["client_id"], "client_secret": CREDS["client_secret"], "grant_type": "refresh_token", "refresh_token": "WxFDKwqScZIQ-1"}
    assert treq.content in (b"", None)
    assert creds["refresh_token"] == "WxFDKwqScZIQ-2"
    req = me.calls[0].request
    _check(req)
    assert req.headers["x-bili-content-md5"] == "d41d8cd98f00b204e9800998ecf8427e"


@pytest.mark.asyncio
@respx.mock
async def test_delete_signs_the_body_md5():
    _token()
    route = respx.post(API + "/archive/delete").mock(return_value=httpx.Response(200, json={"code": 0, "message": "0"}))
    res = await _server().call_tool("delete", {"post_id": "BV1MW421X7gM"})
    assert res.structured_content["status"] == "deleted"
    req = route.calls[0].request
    assert json.loads(req.content) == {"resource_id": "BV1MW421X7gM"}
    _check(req)


@pytest.mark.asyncio
@respx.mock
async def test_analytics_and_error_codes():
    _token()
    route = respx.get(url__startswith=API + "/data/arc/stat").mock(side_effect=[
        httpx.Response(200, json={"code": 0, "data": {"title": "t", "view": 29, "like": 3, "reply": 1}}),
        httpx.Response(200, json={"code": 127002, "message": "sign验证错误"})])
    s = _server()
    a = await s.call_tool("analytics_post", {"post_id": "BV1MW421X7gM"})
    assert a.structured_content["metrics"]["view"] == 29 and route.calls[0].request.url.params["resource_id"] == "BV1MW421X7gM"
    e = await s.call_tool("analytics_post", {"post_id": "x"})
    assert e.is_error is True and CREDS["client_secret"] not in json.dumps(e.structured_content)
