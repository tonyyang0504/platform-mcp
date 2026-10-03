import json
import sys
from pathlib import Path
from urllib.parse import parse_qsl

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ecommerce_suppliers" / "olist_tiny_erp.json").read_text(encoding="utf-8"))
CREDS = {"client_id": "tiny-app", "client_secret": "tiny-secret-0123456789", "refresh_token": "tiny-refresh-aaaaaaaa"}
TOKEN = "https://accounts.tiny.com.br/realms/tiny/protocol/openid-connect/token"
BASE = "https://api.tiny.com.br/public-api/v3"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_refresh_token_grant_and_product_search():
    tok = respx.post(TOKEN).mock(return_value=httpx.Response(200, json={"access_token": "tiny-access-1234567", "expires_in": 14400, "refresh_token": "tiny-refresh-bbbbbbbb"}))
    route = respx.get(f"{BASE}/produtos").mock(return_value=httpx.Response(200, json={"itens": [{"id": 337, "sku": "CAM-01", "descricao": "Camiseta", "situacao": "A", "precos": {"preco": 49.9, "precoCusto": 20}}],
                                                                                        "paginacao": {"limit": 25, "offset": 25, "total": 60}}))
    res = await _server().call_tool("list_products", {"query": "camiseta", "page": 2})
    assert res.is_error is False
    p = res.structured_content["products"][0]
    assert p["id"] == "337" and p["sku"] == "CAM-01" and p["price"] == 49.9 and res.structured_content["total"] == 60
    form = dict(parse_qsl(tok.calls.last.request.content.decode()))
    assert form == {"grant_type": "refresh_token", "refresh_token": "tiny-refresh-aaaaaaaa", "client_id": "tiny-app", "client_secret": "tiny-secret-0123456789"}
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer tiny-access-1234567"
    assert req.url.params["nome"] == "camiseta" and req.url.params["offset"] == "25" and req.url.params["limit"] == "25"


@pytest.mark.asyncio
@respx.mock
async def test_get_product_and_purchase_order():
    respx.post(TOKEN).mock(return_value=httpx.Response(200, json={"access_token": "tiny-access-1234567", "expires_in": 14400}))
    respx.get(f"{BASE}/produtos/337").mock(return_value=httpx.Response(200, json={"id": 337, "sku": "CAM-01", "descricao": "Camiseta", "precos": {"preco": 49.9}, "estoque": {"quantidade": 12},
                                                                                "fornecedores": [{"id": 9, "nome": "Malharia X"}]}))
    respx.get(f"{BASE}/ordem-compra/88").mock(return_value=httpx.Response(200, json={"id": 88, "numeroPedido": "OC-12", "data": "2026-09-01", "situacao": "0", "totalPedidoCompra": 998.0,
                                                                                    "contato": {"nome": "Malharia X"}}))
    s = _server()
    g = await s.call_tool("get_product", {"id": "337"})
    assert g.structured_content["stock"] == 12 and g.structured_content["title"] == "Camiseta"
    o = await s.call_tool("get_order", {"id": "88"})
    assert o.structured_content["id"] == "88" and o.structured_content["total"] == 998.0 and o.structured_content["created_at"] == "2026-09-01"


@pytest.mark.asyncio
@respx.mock
async def test_expired_refresh_token_is_an_auth_error_without_secrets():
    respx.post(TOKEN).mock(return_value=httpx.Response(400, json={"error": "invalid_grant", "error_description": "Token is not active tiny-refresh-aaaaaaaa"}))
    s = _server()
    res = await s.call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "tiny-refresh-aaaaaaaa" not in json.dumps(res.structured_content)
    assert sorted(t.name for t in await s.list_tools()) == ["get_order", "get_product", "list_products", "me"]
