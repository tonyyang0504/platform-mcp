import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "taobao_fenxiao_alimama.json").read_text(encoding="utf-8"))
CREDS = {"app_key": "23456789", "app_secret": "tbk-secret-0987", "adzone_id": "12345678"}
GW = "https://gw.api.taobao.com/router/rest"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _check(request):
    q = dict(parse_qsl(urlsplit(str(request.url)).query, keep_blank_values=True))
    sig = q.pop("sign")
    assert sig == hashlib.md5((CREDS["app_secret"] + "".join(k + q[k] for k in sorted(q)) + CREDS["app_secret"]).encode()).hexdigest().upper()
    assert "session" not in q and q["app_key"] == "23456789"
    return q


@pytest.mark.asyncio
@respx.mock
async def test_material_search_for_the_adzone(monkeypatch):
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1790301600.0)
    route = respx.get(url__startswith=GW).mock(return_value=httpx.Response(200, json={"tbk_dg_material_optional_upgrade_response": {"total_results": 1212, "result_list": {"map_data": [{
        "item_id": "qeqscd1231-uqwenqe", "item_basic_info": {"title": "复古女裤子", "pict_url": "//img.alicdn.com/x.jpg", "shop_title": "魔黛娅", "volume": 30},
        "price_promotion_info": {"zk_final_price": "79.9", "final_promotion_price": "69.9"}, "publish_info": {"click_url": "//s.click.taobao.com/x", "income_rate": "5.50"}}]}}}))
    res = await _server().call_tool("list_products", {"query": "女装", "limit": 20})
    p = res.structured_content["products"][0]
    assert p["id"] == "qeqscd1231-uqwenqe" and p["title"] == "复古女裤子" and p["price"] == "79.9" and p["final_price"] == "69.9"
    q = _check(route.calls[0].request)
    assert q["method"] == "taobao.tbk.dg.material.optional.upgrade" and q["q"] == "女装" and q["adzone_id"] == "12345678" and q["page_size"] == "20"
    assert q["timestamp"] == "2026-09-25 10:00:00"


@pytest.mark.asyncio
@respx.mock
async def test_item_info_and_time_probe():
    def handler(request):
        q = _check(request)
        if q["method"] == "taobao.time.get":
            return httpx.Response(200, json={"time_get_response": {"time": "2026-09-25 10:00:00"}})
        assert q["num_iids"] == "556633720749"
        return httpx.Response(200, json={"tbk_item_info_get_response": {"results": {"n_tbk_item": [{"num_iid": "556633720749", "title": "连衣裙", "zk_final_price": "88.00", "item_url": "http://detail.tmall.com/item.htm?id=556633720749"}]}}})
    respx.get(url__startswith=GW).mock(side_effect=handler)
    s = _server()
    assert (await s.call_tool("me", {})).is_error is False
    g = await s.call_tool("get_product", {"id": "556633720749"})
    assert g.structured_content["title"] == "连衣裙" and g.structured_content["price"] == "88.00"


@pytest.mark.asyncio
@respx.mock
async def test_error_response():
    respx.get(url__startswith=GW).mock(return_value=httpx.Response(200, json={"error_response": {"code": 25, "msg": "Invalid signature"}}))
    res = await _server().call_tool("list_products", {"query": "x"})
    assert res.is_error is True and CREDS["app_secret"] not in json.dumps(res.structured_content)
