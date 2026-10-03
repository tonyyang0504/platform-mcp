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

SPEC = json.loads((ROOT / "catalog" / "trading" / "bybit.json").read_text(encoding="utf-8"))
CREDS = {"api_key": "KEY-bybit-abcdef", "api_secret": "SECRET-bybit-abcdef"}


def _server(category="linear"):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {**CREDS, "category": category}, 50, "test", envelope=a["envelope"]))


def _expected_sign(req):
    # bybit v5 guide: HMAC_SHA256(timestamp + api_key + recv_window + queryString | jsonBodyString), lowercase hex
    ts = req.headers["X-BAPI-TIMESTAMP"]
    payload = f"{ts}{CREDS['api_key']}5000{req.url.query.decode()}{req.content.decode()}"
    return hmac.new(CREDS["api_secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_all_verbs_offered_with_category_config():
    tools = {t.name: t for t in await _server().list_tools()}
    assert len(tools) == 8 and SPEC["adapter"]["not_offered"] == {}
    assert tools["place_order"].annotations.destructive_hint is True and "api-testnet.bybit.com" in tools["place_order"].description
    assert [f["name"] for f in SPEC["adapter"]["config_fields"]] == ["category"]


@pytest.mark.asyncio
@respx.mock
async def test_get_request_signs_the_query_string_and_maps_klines():
    route = respx.get(url__startswith="https://api.bybit.com/v5/market/kline").mock(return_value=httpx.Response(200, json={
        "retCode": 0, "retMsg": "OK", "result": {"symbol": "BTCUSDT", "category": "linear", "list": [
            ["1790262000000", "83625.8", "83672.7", "83452.9", "83515.1", "381.377", "31865278.4737"]]}, "retExtInfo": {}, "time": 1}))
    res = await _server().call_tool("get_candles", {"symbol": "BTCUSDT", "interval": "4h", "limit": 3})
    assert res.is_error is False
    c = res.structured_content["candles"][0]
    assert (c["time"], c["open"], c["close"], c["volume"]) == ("1790262000000", 83625.8, 83515.1, 381.377)
    req = route.calls[0].request
    assert req.url.params["category"] == "linear" and req.url.params["interval"] == "240" and req.url.params["limit"] == "3"
    assert req.headers["X-BAPI-API-KEY"] == CREDS["api_key"] and req.headers["X-BAPI-RECV-WINDOW"] == "5000"
    assert req.headers["X-BAPI-SIGN"] == _expected_sign(req) and CREDS["api_secret"] not in str(req.headers)


@pytest.mark.asyncio
@respx.mock
async def test_place_order_signs_the_exact_json_body():
    route = respx.post("https://api.bybit.com/v5/order/create").mock(return_value=httpx.Response(200, json={
        "retCode": 0, "retMsg": "OK", "result": {"orderId": "1321003749386327552", "orderLinkId": "spot-test-postonly"}, "retExtInfo": {}, "time": 1}))
    res = await _server("spot").call_tool("place_order", {"symbol": "BTCUSDT", "side": "buy", "type": "market", "quantity": 0.002})
    assert res.is_error is False and res.structured_content["order_id"] == "1321003749386327552" and res.structured_content["status"] == "submitted"
    req = route.calls[0].request
    assert json.loads(req.content) == {"category": "spot", "symbol": "BTCUSDT", "side": "Buy", "orderType": "Market", "qty": "0.002", "marketUnit": "baseCoin"}
    assert req.url.query == b"" and req.headers["X-BAPI-SIGN"] == _expected_sign(req)
    await _server("linear").call_tool("place_order", {"symbol": "BTCUSDT", "side": "sell", "type": "limit", "quantity": 1, "price": 90000})
    body = json.loads(route.calls[1].request.content)
    assert body["orderType"] == "Limit" and body["price"] == "90000" and body["side"] == "Sell" and body["marketUnit"] == ""


@pytest.mark.asyncio
@respx.mock
async def test_nonzero_retcode_is_an_error_and_list_orders_sends_settle_coin():
    respx.post("https://api.bybit.com/v5/order/cancel").mock(return_value=httpx.Response(200, json={"retCode": 110001, "retMsg": "order not exists or too late to cancel"}))
    bad = await _server().call_tool("cancel_order", {"order_id": "o2", "symbol": "BTCUSDT"})
    assert bad.is_error is True and "order not exists" in bad.content[0].text and CREDS["api_secret"] not in bad.content[0].text
    route = respx.get(url__startswith="https://api.bybit.com/v5/order/realtime").mock(return_value=httpx.Response(200, json={
        "retCode": 0, "retMsg": "OK", "result": {"list": [{"orderId": "fd4300ae", "orderLinkId": "", "symbol": "ETHUSDT", "side": "Buy", "orderType": "Limit",
                                                           "orderStatus": "New", "price": "1600.00", "qty": "0.10", "cumExecQty": "0.00", "createdTime": "1684738540559"}], "nextPageCursor": ""}}))
    res = await _server().call_tool("list_orders", {})
    assert res.structured_content["orders"][0]["order_id"] == "fd4300ae" and res.structured_content["orders"][0]["status"] == "New"
    assert route.calls[0].request.url.params["settleCoin"] == "USDT"
    await _server("spot").call_tool("list_orders", {"symbol": "BTCUSDT"})
    assert "settleCoin" not in route.calls[1].request.url.params
