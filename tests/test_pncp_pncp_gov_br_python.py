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

SPEC = json.loads((ROOT / "catalog" / "deals" / "pncp_pncp_gov_br.json").read_text(encoding="utf-8"))
URL = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"

# row as returned live on 2026-09-25, trimmed
ROW = {
    "orgaoEntidade": {"cnpj": "00394460000141", "razaoSocial": "MINISTERIO DA FAZENDA"},
    "unidadeOrgao": {"ufSigla": "PR", "municipioNome": "Foz do Iguaçu"},
    "dataPublicacaoPncp": "2022-05-04T16:37:44", "objetoCompra": "Contratação de manutenção de balança rodoviária",
    "dataEncerramentoProposta": "2030-05-10T07:59:59", "linkSistemaOrigem": "https://www.comprasnet.gov.br/acesso.asp?url=/proposta-170162-08-00007-2022",
    "numeroControlePNCP": "00394460000141-1-000224/2022", "valorTotalEstimado": 37553.33, "modalidadeId": 8, "informacaoComplementar": "Observa o limite legal",
}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_search_is_offered():
    assert [t.name for t in await _server().list_tools()] == ["search_postings"]


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_open_window_modality_and_paging():
    route = respx.get(URL).mock(return_value=httpx.Response(200, json={"data": [ROW], "totalRegistros": 38780, "totalPaginas": 3878, "numeroPagina": 2}))
    res = await _server().call_tool("search_postings", {"query": "balança", "category": "8", "page": 2, "limit": 10, "min_budget": 1000})
    assert res.is_error is False
    assert dict(route.calls.last.request.url.params) == {"codigoModalidadeContratacao": "8", "pagina": "2", "tamanhoPagina": "10", "dataFinal": "20991231"}
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == "00394460000141-1-000224/2022" and p["buyer"] == "MINISTERIO DA FAZENDA" and p["budget_max"] == 37553.33
    assert p["deadline"] == "2030-05-10T07:59:59" and p["url"].startswith("https://www.comprasnet.gov.br/")
    assert sc["total"] == 38780


@pytest.mark.asyncio
@respx.mock
async def test_limit_is_capped_at_50_and_204_is_empty():
    route = respx.get(URL).mock(return_value=httpx.Response(204))
    res = await _server().call_tool("search_postings", {"page": 99999, "limit": 100})
    assert res.is_error is False and res.structured_content["postings"] == []
    assert route.calls.last.request.url.params["tamanhoPagina"] == "50"


@pytest.mark.asyncio
@respx.mock
async def test_page_size_below_ten_is_invalid_input_and_bad_category_is_invalid():
    respx.get(URL).mock(return_value=httpx.Response(400, json={"message": "must be greater than or equal to 10", "status": "400", "error": "Bad Request"}))
    res = await _server().call_tool("search_postings", {"limit": 5})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input"
    bad = await _server().call_tool("search_postings", {"category": "pregão"})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"
