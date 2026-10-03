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

SPEC = json.loads((ROOT / "catalog" / "deals" / "zbj.json").read_text(encoding="utf-8"))
ROUTER = "https://openapi.zbj.com/router"
CREDS = {"app_key": "2016061718xxxxxx001", "app_secret": "00A583ED7F8D1234353F67E9583123456", "access_token": "d3aaf29a64c4d8d62725b1f16009", "openid": "94F065687A591BCB65BE6F2C9BFDA18E"}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope"))
    return build_server(SPEC, transport=t)


def _expected_sign(params: dict) -> str:
    s = CREDS["app_secret"] + "".join(k + v for k, v in sorted((k, v) for k, v in params.items() if k != "sign")) + CREDS["app_secret"]
    return hashlib.sha1(s.encode()).hexdigest().upper()


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_signed_router_call():
    route = respx.get(ROUTER).mock(return_value=httpx.Response(200, json={
        "taskId": 6047675, "createTime": 1444970059, "successToken": "@@$-SUCCESS_TOKEN$-@@", "nickname": "zhigb_0059",
        "content": "logo design", "amount": 3000, "title": "Logo", "mode": 2}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["get_posting", "me"]
    res = await server.call_tool("get_posting", {"id": "6047675"})
    p = res.structured_content
    assert p["id"] == 6047675 or p["id"] == "6047675"
    assert p["title"] == "Logo" and p["buyer"] == "zhigb_0059" and p["budget_max"] == 3000 and p["currency"] == "CNY"
    q = dict(route.calls.last.request.url.params)
    assert q["method"] == "zbj.task.getDetailById" and q["v"] == "1.0" and q["format"] == "json" and q["taskId"] == "6047675"
    assert q["appKey"] == CREDS["app_key"] and q["accessToken"] == CREDS["access_token"] and len(q["timestamp"]) == 13
    assert "app_secret" not in q and CREDS["app_secret"] not in str(route.calls.last.request.url)
    assert q["sign"] == _expected_sign(q) and len(q["sign"]) == 40


@pytest.mark.asyncio
@respx.mock
async def test_me_and_error_envelope():
    route = respx.get(ROUTER).mock(return_value=httpx.Response(200, json={"nickname": "哈哈", "userName": "dukelynn", "openid": CREDS["openid"]}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["userName"] == "dukelynn"
    assert route.calls.last.request.url.params["openid"] == CREDS["openid"]
    respx.get(ROUTER).mock(return_value=httpx.Response(200, json={"errorToken": "@@$-ERROR_TOKEN$-@@", "code": "22", "message": "缺少应用键参数:appKey", "solution": "..."}))
    bad = await _server().call_tool("get_posting", {"id": "1"})
    assert bad.is_error is True
