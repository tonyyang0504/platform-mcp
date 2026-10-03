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

SPEC = json.loads((ROOT / "catalog" / "marketplaces" / "hotmart.json").read_text(encoding="utf-8"))
TOKEN = "https://api-sec-vlc.hotmart.com/security/oauth/token"
BASE = "https://developers.hotmart.com"
CREDS = {"client_id": "cid-abc", "client_secret": "SECRETxyz", "basic_token": "BASICtoken64"}
SALE = {"product": {"name": "Product06", "id": 2125812}, "buyer": {"name": "Ian", "email": "ian@teste.com"},
        "purchase": {"transaction": "HP12455690122399", "order_date": 1622948400000, "status": "APPROVED",
                     "price": {"value": 235.76, "currency_code": "USD"}}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], dict(CREDS), 50, "test")
    return build_server(SPEC, transport=t)


def _token():
    return respx.post(url__startswith=TOKEN).mock(return_value=httpx.Response(200, json={"access_token": "AT-1", "token_type": "bearer", "expires_in": 172799}))


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    assert sorted(t.name for t in await _server().list_tools()) == ["get_product", "get_sales_stats", "list_products", "list_refunds", "list_sales", "me", "refund"]


@pytest.mark.asyncio
@respx.mock
async def test_token_request_puts_credentials_in_the_url_and_sends_the_basic_value():
    tok = _token()
    respx.get(BASE + "/user/api/v1/me").mock(return_value=httpx.Response(200, json={"id": 1, "name": "Maria"}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["name"] == "Maria"
    req = tok.calls.last.request
    assert req.url.params["grant_type"] == "client_credentials" and req.url.params["client_id"] == "cid-abc" and req.url.params["client_secret"] == "SECRETxyz"
    assert req.headers["Authorization"] == "Basic BASICtoken64" and req.headers["Content-Type"] == "application/json"
    assert json.loads(req.content)["grant_type"] == "client_credentials"


@pytest.mark.asyncio
@respx.mock
async def test_list_sales_uses_epoch_ms_and_the_page_token_cursor():
    _token()
    route = respx.get(BASE + "/payments/api/v1/sales/history").mock(return_value=httpx.Response(200, json={
        "items": [SALE], "page_info": {"total_results": 1, "next_page_token": "eyJwIjoyfQ==", "results_per_page": 1}}))
    res = await _server().call_tool("list_sales", {"since": "2021-06-01", "limit": 10, "cursor": "eyJwIjoxfQ==", "product_id": "2125812"})
    assert res.is_error is False, res.structured_content
    s = res.structured_content["sales"][0]
    assert s["id"] == "HP12455690122399" and s["amount"] == 235.76 and s["currency"] == "USD" and s["customer_email"] == "ian@teste.com"
    assert res.structured_content["next_cursor"] == "eyJwIjoyfQ=="
    q = route.calls.last.request.url.params
    assert q["start_date"] == "1622505600000" and q["max_results"] == "10" and q["page_token"] == "eyJwIjoxfQ==" and q["product_id"] == "2125812"
    assert route.calls.last.request.headers["Authorization"] == "Bearer AT-1"


@pytest.mark.asyncio
@respx.mock
async def test_refunds_filter_stats_and_refund_call():
    _token()
    hist = respx.get(BASE + "/payments/api/v1/sales/history").mock(return_value=httpx.Response(200, json={"items": [SALE], "page_info": {}}))
    respx.get(BASE + "/payments/api/v1/sales/summary").mock(return_value=httpx.Response(200, json={"items": [{"total_items": 2, "total_value": {"value": 3.7, "currency_code": "USD"}}]}))
    ref = respx.put(BASE + "/payments/api/v1/sales/HP12455690122399/refund").mock(return_value=httpx.Response(200, text=""))
    r = await _server().call_tool("list_refunds", {})
    assert r.structured_content["refunds"][0]["sale_id"] == "HP12455690122399"
    assert hist.calls.last.request.url.params["transaction_status"] == "REFUNDED"
    st = await _server().call_tool("get_sales_stats", {"since": "2021-06-01", "until": "2021-06-30"})
    assert st.structured_content["revenue"] == 3.7 and st.structured_content["sales"] == 2 and st.structured_content["currency"] == "USD"
    done = await _server().call_tool("refund", {"sale_id": "HP12455690122399"})
    assert done.is_error is False and done.structured_content["status"] == "requested" and ref.called
