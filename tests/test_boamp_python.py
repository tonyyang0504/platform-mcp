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

SPEC = json.loads((ROOT / "catalog" / "deals" / "boamp.json").read_text(encoding="utf-8"))
URL = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"

# record as returned live on 2026-09-25, trimmed
REC = {
    "idweb": "26-91551", "id": "26_91551", "objet": "Mission de maîtrise d'œuvre pour la restauration de la toiture de l'hôtel de ville de Vichy",
    "famille": "JOUE", "dateparution": "2026-09-24", "datelimitereponse": "2026-10-26T11:00:00+00:00", "nomacheteur": "COMMUNE DE VICHY",
    "nature_categorise_libelle": "Avis de marché", "descripteur_libelle": ["Maîtrise d'oeuvre"], "url_avis": "https://www.boamp.fr/pages/avis/?q=idweb:26-91551",
}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_are_read_only_search_and_get():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search_postings"]
    assert all(t.annotations.read_only_hint for t in tools)


@pytest.mark.asyncio
@respx.mock
async def test_search_quotes_the_query_refines_category_and_pages_by_offset():
    route = respx.get(URL).mock(return_value=httpx.Response(200, json={"total_count": 209, "results": [REC]}))
    res = await _server().call_tool("search_postings", {"query": "toiture vichy", "category": "Maîtrise d'oeuvre", "page": 3, "limit": 10, "min_budget": 5})
    assert res.is_error is False
    q = dict(route.calls.last.request.url.params)
    assert q == {"where": '"toiture vichy"', "refine": "descripteur_libelle:Maîtrise d'oeuvre", "limit": "10", "offset": "20", "order_by": "dateparution desc"}
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == "26-91551" and p["buyer"] == "COMMUNE DE VICHY" and p["deadline"] == "2026-10-26T11:00:00+00:00"
    assert p["url"] == "https://www.boamp.fr/pages/avis/?q=idweb:26-91551" and p["skills"] == ["Maîtrise d'oeuvre"]
    assert sc["total"] == 209


@pytest.mark.asyncio
@respx.mock
async def test_search_without_query_sends_no_where():
    route = respx.get(URL).mock(return_value=httpx.Response(200, json={"total_count": 0, "results": []}))
    res = await _server().call_tool("search_postings", {})
    assert res.is_error is False
    assert "where" not in route.calls.last.request.url.params and "refine" not in route.calls.last.request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_filters_on_idweb_and_empty_is_not_found():
    route = respx.get(URL).mock(side_effect=[httpx.Response(200, json={"total_count": 1, "results": [REC]}), httpx.Response(200, json={"total_count": 0, "results": []})])
    ok = await _server().call_tool("get_posting", {"id": "26-91551"})
    assert ok.is_error is False and ok.structured_content["title"].startswith("Mission de maîtrise")
    assert route.calls.last.request.url.params["where"] == 'idweb="26-91551"' and route.calls.last.request.url.params["limit"] == "1"
    miss = await _server().call_tool("get_posting", {"id": "00-00000"})
    assert miss.is_error is True and miss.structured_content["error"] == "not_found"


@pytest.mark.asyncio
@respx.mock
async def test_odsql_syntax_error_is_invalid_input():
    respx.get(URL).mock(return_value=httpx.Response(400, json={"error_code": "ODSQLSyntaxError", "message": "ODSQL syntax exception: unexpected end of line"}))
    res = await _server().call_tool("search_postings", {"query": 'a"b'})
    assert res.is_error is True and res.structured_content["error"] == "invalid_input" and "ODSQL" in res.structured_content["message"]
