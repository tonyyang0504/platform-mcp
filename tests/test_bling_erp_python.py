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

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "bling_erp.json").read_text(encoding="utf-8"))
API = "https://api.bling.com.br/Api/v3"
TOKEN_URL = f"{API}/oauth/token"
CREDS = {"client_id": "cid", "client_secret": "csecretVALUE", "refresh_token": "rtSECRET1"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test"))


def _tok(access="acc-1", refresh="rtSECRET2"):
    return httpx.Response(200, json={"access_token": access, "expires_in": 21600, "token_type": "Bearer", "scope": "1 2", "refresh_token": refresh})


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_order", "get_product", "list_products", "me"]


@pytest.mark.asyncio
@respx.mock
async def test_refresh_uses_basic_client_auth_then_bearer():
    token = respx.post(TOKEN_URL).mock(return_value=_tok())
    me = respx.get(f"{API}/empresas/me/dados-basicos").mock(return_value=httpx.Response(200, json={"data": {"id": "12345678", "nome": "Loja", "cnpj": "00.000.000/0001-00"}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["data"]["nome"] == "Loja"
    req = token.calls[0].request
    assert parse_qs(req.content.decode()) == {"grant_type": ["refresh_token"], "refresh_token": ["rtSECRET1"]}
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(b"cid:csecretVALUE").decode()
    assert me.calls[0].request.headers["Authorization"] == "Bearer acc-1"


@pytest.mark.asyncio
@respx.mock
async def test_list_products_maps_page_limit_and_name():
    respx.post(TOKEN_URL).mock(return_value=_tok())
    respx.get(f"{API}/produtos").mock(return_value=httpx.Response(200, json={"data": [
        {"id": 12345678, "nome": "Copo do Bling", "codigo": "COD-4587", "preco": 4.99, "precoCusto": 4.99, "estoque": {"saldoVirtualTotal": 13},
         "tipo": "P", "situacao": "A", "formato": "S", "imagemURL": "https://www.bling.com.br/img.png"}]}))
    res = await _server().call_tool("list_products", {"query": "Copo", "category": "77", "page": 2, "limit": 10})
    p = res.structured_content["products"][0]
    assert p["id"] == "12345678" and p["title"] == "Copo do Bling" and p["sku"] == "COD-4587" and p["price"] == 4.99 and p["currency"] == "BRL"
    assert p["stock_balance"] == 13
    q = respx.calls.last.request.url.params
    assert q["pagina"] == "2" and q["limite"] == "10" and q["nome"] == "Copo" and q["idCategoria"] == "77"


@pytest.mark.asyncio
@respx.mock
async def test_get_order_reads_a_purchase_order():
    respx.post(TOKEN_URL).mock(return_value=_tok())
    respx.get(f"{API}/pedidos/compras/555").mock(return_value=httpx.Response(200, json={"data": {
        "id": 555, "numero": 12, "data": "2026-09-01", "dataPrevista": "2026-09-10", "total": 150.5, "fornecedor": {"id": 9}, "situacao": {"id": 1, "valor": 0}}}))
    sc = (await _server().call_tool("get_order", {"id": "555"})).structured_content
    assert sc["id"] == "555" and sc["total"] == 150.5 and sc["status_code"] == 0 and sc["supplier_id"] == "9"


@pytest.mark.asyncio
@respx.mock
async def test_expired_refresh_token_is_an_auth_error_without_secrets():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": {"type": "invalid_grant", "message": "Invalid refresh token rtSECRET1"}}))
    res = await _server().call_tool("list_products", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    blob = json.dumps(res.structured_content)
    assert "rtSECRET1" not in blob and "csecretVALUE" not in blob
