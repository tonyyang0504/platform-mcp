import base64
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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_channels" / "yahoo_shopping_jp.json").read_text(encoding="utf-8"))
API = "https://circus.shopping.yahooapis.jp/ShoppingWebService/V1"
XML = {"content-type": "application/xml;charset=UTF-8"}


def _server():
    a = SPEC["adapter"]
    creds = {"client_id": "CID-yj", "client_secret": "SECRET-yj-1", "refresh_token": "REFRESH-yj-1", "seller_id": "teststore"}
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], creds, 50, "test"))


def _token():
    return respx.post("https://auth.login.yahoo.co.jp/yconnect/v2/token").mock(return_value=httpx.Response(200, json={"access_token": "ACCESS-yj", "token_type": "bearer", "expires_in": 3600}))


@pytest.mark.asyncio
async def test_tools():
    assert sorted(t.name for t in await _server().list_tools()) == ["end_listing", "me", "set_inventory", "update_listing"]


@pytest.mark.asyncio
@respx.mock
async def test_refresh_grant_then_bearer_probe_with_xml_answer():
    tok = _token()
    me = respx.get(url__startswith=f"{API}/stCategoryList").mock(return_value=httpx.Response(200, headers=XML, text='<?xml version="1.0" encoding="UTF-8" ?><ResultSet totalResultsAvailable="1"><Result><PageKey>c3e6b8c5a5</PageKey><Name>カテゴリ1</Name></Result></ResultSet>'))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["ResultSet"]["Result"]["PageKey"] == "c3e6b8c5a5"
    t = tok.calls[0].request
    assert t.headers["Authorization"] == "Basic " + base64.b64encode(b"CID-yj:SECRET-yj-1").decode()
    assert parse_qs(t.content.decode()) == {"grant_type": ["refresh_token"], "refresh_token": ["REFRESH-yj-1"]}
    assert me.calls[0].request.headers["Authorization"] == "Bearer ACCESS-yj" and me.calls[0].request.url.params["seller_id"] == "teststore"


@pytest.mark.asyncio
@respx.mock
async def test_set_stock_form_post():
    _token()
    route = respx.post(f"{API}/setStock").mock(return_value=httpx.Response(200, headers=XML, text='<ResultSet totalResultsAvailable="1" totalResultsReturned="1" firstResultPosition="1"><Result><ItemCode>item-01</ItemCode><SubCode>sub-01</SubCode><Quantity>11</Quantity></Result></ResultSet>'))
    res = await _server().call_tool("set_inventory", {"sku": "item-01:sub-01", "quantity": 11})
    assert res.is_error is False and res.structured_content["status"] == "stock_updated" and res.structured_content["stock"] == "11"
    assert parse_qs(route.calls[0].request.content.decode()) == {"seller_id": ["teststore"], "item_code": ["item-01:sub-01"], "quantity": ["11"]}


@pytest.mark.asyncio
@respx.mock
async def test_update_items_encodes_item1_and_end_listing_hides_page():
    _token()
    route = respx.post(f"{API}/updateItems").mock(return_value=httpx.Response(200, headers=XML, text='<?xml version="1.0" encoding="UTF-8" ?><ResultSet><Status>OK</Status></ResultSet>'))
    server = _server()
    res = await server.call_tool("update_listing", {"listing_id": "abc1", "price": 1980})
    assert res.is_error is False and res.structured_content["status"] == "OK"
    body = route.calls[0].request.content.decode()
    assert "item1=item_code%3Dabc1%26price%3D1980%26sale_price%3D" in body
    assert parse_qs(body)["item1"] == ["item_code=abc1&price=1980&sale_price="]
    assert (await server.call_tool("end_listing", {"listing_id": "abc1"})).is_error is False
    assert parse_qs(route.calls[1].request.content.decode())["item1"] == ["item_code=abc1&display=0"]


@pytest.mark.asyncio
@respx.mock
async def test_xml_error_400_is_an_error():
    _token()
    respx.post(f"{API}/setStock").mock(return_value=httpx.Response(400, headers=XML, text="<Error><Message>パラメータ「item_code」が不正です。</Message><Code>st-02101</Code></Error>"))
    res = await _server().call_tool("set_inventory", {"sku": "bad code", "quantity": 1})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
