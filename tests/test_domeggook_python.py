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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "domeggook.json").read_text(encoding="utf-8"))
API = "https://www.domeggook.com/ssl/api/"


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], {"api_key": "dmg-key-123"}, 50, "test", envelope=a["envelope"])
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_open_api_tools_only():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_product", "list_products", "me"]


@pytest.mark.asyncio
@respx.mock
async def test_list_products_searches_the_dome_market_with_the_aid_key():
    # openapi.domeggook.com 상품리스트 v4.1: {domeggook{header{numberOfItems}, list{item[{no, title, price, thumb, unitQty, url}]}}}
    route = respx.get(API).mock(return_value=httpx.Response(200, json={"domeggook": {
        "header": {"numberOfItems": 704, "currentPage": 1, "itemsPerPage": 2, "numberOfPages": 352},
        "list": {"item": [{"no": 7914900, "title": "마스크 50매", "price": 3800, "thumb": "https://cdn1.domeggook.com/x.jpg", "unitQty": 10, "id": "seller1", "url": "https://domeggook.com/7914900", "deli": {"who": "P", "fee": "3000"}}]}}}))
    res = await _server().call_tool("list_products", {"query": "마스크", "limit": 2})
    sc = res.structured_content
    assert res.is_error is False and sc["total"] == 704
    p = sc["products"][0]
    assert p["id"] == "7914900" and p["price"] == 3800 and p["currency"] == "KRW" and p["moq"] == 10
    q = route.calls.last.request.url.params
    assert q["aid"] == "dmg-key-123" and q["mode"] == "getItemList" and q["market"] == "dome" and q["kw"] == "마스크" and q["sz"] == "2" and q["om"] == "json"


@pytest.mark.asyncio
@respx.mock
async def test_get_product_reads_the_item_view():
    respx.get(API).mock(return_value=httpx.Response(200, json={"domeggook": {"basis": {"no": 12345678, "status": "판매중", "title": "샐러드 드레싱 285g"},
        "price": {"dome": "1+3800|20+3500", "supply": 3900}, "qty": {"inventory": 500, "domeMoq": 1, "supplyUnit": 1}, "deli": {"method": "택배"}}}))
    res = await _server().call_tool("get_product", {"id": "12345678"})
    sc = res.structured_content
    assert sc["id"] == "12345678" and sc["title"] == "샐러드 드레싱 285g" and sc["stock"] == 500


@pytest.mark.asyncio
@respx.mock
async def test_errors_in_a_200_body_are_tool_errors_without_the_key():
    respx.get(API).mock(return_value=httpx.Response(200, json={"errors": {"code": "401", "message": "API 인증 실패", "dcode": "UNAUTHORIZED", "dmessage": "유효하지 않은 API Key 입니다. dmg-key-123"}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True
    assert "dmg-key-123" not in json.dumps(res.structured_content, ensure_ascii=False)
