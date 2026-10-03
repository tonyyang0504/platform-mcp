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

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "zhubajie.json").read_text(encoding="utf-8"))
ROUTER = "https://openapi.zbj.com/router"
CREDS = {"app_key": "2016061718xxxxxx001", "app_secret": "00A583ED7F8D1234353F67E9583123456", "access_token": "ab4ce0912633b98160f4db71d5cea34b", "openid": "7DB78F3D17312EFA6BA125B1E9EA9C68"}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope"))
    return build_server(SPEC, transport=t)


def _expected_sign(params: dict) -> str:
    s = CREDS["app_secret"] + "".join(k + v for k, v in sorted((k, v) for k, v in params.items() if k != "sign")) + CREDS["app_secret"]
    return hashlib.sha1(s.encode()).hexdigest().upper()


@pytest.mark.asyncio
@respx.mock
async def test_tools_and_list_products_signed():
    route = respx.get(ROUTER).mock(return_value=httpx.Response(200, json={
        "successToken": "@@$-SUCCESS_TOKEN$-@@", "processing": False, "pages": 1, "total": 3,
        "serviceList": [{"serviceId": 1001966264, "subject": "LOGO设计", "serviceurl": "http://shop.zbj.com/58/sid-1001966264.html",
                         "amount": 100, "amountApp": 100, "sales": 0, "state": 2, "lasttime": 1473048096, "addtime": 1473048096}]}))
    server = _server()
    assert sorted(t.name for t in await server.list_tools()) == ["list_products", "list_refunds", "list_sales", "me"]
    res = await server.call_tool("list_products", {"page": 2, "limit": 10})
    out = res.structured_content
    assert res.is_error is False and out["total"] == 3
    p = out["products"][0]
    assert p["id"] == "1001966264" and p["name"] == "LOGO设计" and p["price"] == 100 and p["currency"] == "CNY"
    q = dict(route.calls.last.request.url.params)
    assert q["method"] == "zbj.service.getServiceList" and q["v"] == "1.0" and q["format"] == "json" and q["state"] == "1"
    assert q["openid"] == CREDS["openid"] and q["pageNum"] == "2" and q["pageSize"] == "10"
    assert q["appKey"] == CREDS["app_key"] and q["accessToken"] == CREDS["access_token"] and len(q["timestamp"]) == 13
    assert CREDS["app_secret"] not in str(route.calls.last.request.url)
    assert q["sign"] == _expected_sign(q) and len(q["sign"]) == 40


@pytest.mark.asyncio
@respx.mock
async def test_list_sales_since_as_compact_datetime():
    route = respx.get(ROUTER).mock(return_value=httpx.Response(200, json={
        "successToken": "@@$-SUCCESS_TOKEN$-@@", "total": 1, "totalPage": 1, "currentPage": 1, "pageSize": 10,
        "tradeInfos": [{"taskId": 7557549, "title": "测试SUBJECT0621", "amount": 100, "taskMode": 11, "taskState": 3, "createtime": 1473405463}]}))
    res = await _server().call_tool("list_sales", {"since": "2026-09-01"})
    s = res.structured_content["sales"][0]
    assert s["id"] == "7557549" and s["product_name"] == "测试SUBJECT0621" and s["amount"] == 100 and s["currency"] == "CNY"
    q = dict(route.calls.last.request.url.params)
    assert q["method"] == "zbj.trade.querySoldServices" and q["startTime"] == "20260901000000" and q["currentPage"] == "1"


@pytest.mark.asyncio
@respx.mock
async def test_list_refunds_and_me():
    respx.get(ROUTER).mock(side_effect=lambda req: httpx.Response(200, json=(
        {"successToken": "@@$-SUCCESS_TOKEN$-@@", "refundInfoList": [{"refundId": 101029, "taskId": 7574444, "refundAmount": 200, "refundState": 5, "createTime": 1478748677, "description": "不满意"}]}
        if req.url.params["method"] == "zbj.trade.getRefundList" else
        {"successToken": "@@$-SUCCESS_TOKEN$-@@", "nickname": "哈哈", "username": "dukelynn", "openid": CREDS["openid"]})))
    r = (await _server().call_tool("list_refunds", {})).structured_content["refunds"][0]
    assert r["id"] == "101029" and r["sale_id"] == "7574444" and r["amount"] == 200 and r["reason"] == "不满意"
    me = await _server().call_tool("me", {})
    assert me.is_error is False and me.structured_content["account"]["username"] == "dukelynn"


@pytest.mark.asyncio
@respx.mock
async def test_error_envelope():
    respx.get(ROUTER).mock(return_value=httpx.Response(200, json={
        "errorToken": "@@$-ERROR_TOKEN$-@@", "code": "9", "message": "服务方法(zbj.service.getServiceList:1.0)业务逻辑出错", "solution": "..."}))
    bad = await _server().call_tool("list_products", {})
    assert bad.is_error is True
