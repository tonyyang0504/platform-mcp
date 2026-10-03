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

SPEC = json.loads((ROOT / "catalog" / "sales" / "no_brreg.json").read_text(encoding="utf-8"))

ENHET = {"organisasjonsnummer": "923609016", "navn": "EQUINOR ASA", "hjemmeside": "www.equinor.com",
         "forretningsadresse": {"land": "Norge", "landkode": "NO", "postnummer": "4035", "poststed": "STAVANGER", "adresse": ["Forusbeen 50"]},
         "naeringskode1": {"kode": "06.100", "beskrivelse": "Utvinning av råolje"}, "antallAnsatte": 21272, "stiftelsesdato": "1972-09-18"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_sales_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_company", "me", "search"]
    search = next(t for t in tools if t.name == "search")
    assert search.annotations.read_only_hint is True and search.input_schema["required"] == ["query"]
    assert search.meta["platform_mcp/endpoint"] == "/enheter"


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_a_zero_based_page_and_maps_documented_fields():
    respx.get("https://data.brreg.no/enhetsregisteret/api/enheter").mock(return_value=httpx.Response(200, json={
        "_embedded": {"enheter": [ENHET]}, "page": {"size": 1, "totalElements": 240, "totalPages": 240, "number": 1}}))
    res = await _server().call_tool("search", {"query": "equinor", "page": 2, "limit": 1})
    assert res.is_error is False
    c = res.structured_content["companies"][0]
    assert c["id"] == "923609016" and c["name"] == "EQUINOR ASA" and c["country"] == "NO" and c["address"] == "Forusbeen 50"
    assert c["industry"] == "Utvinning av råolje" and c["founded"] == "1972-09-18" and c["website"] == "www.equinor.com"
    assert res.structured_content["total"] == 240 and res.structured_content["next_page"] == 3
    req = respx.calls.last.request
    assert req.url.params["navn"] == "equinor" and req.url.params["size"] == "1" and req.url.params["page"] == "1"
    assert "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_get_company_by_organisation_number():
    respx.get("https://data.brreg.no/enhetsregisteret/api/enheter/923609016").mock(return_value=httpx.Response(200, json=ENHET))
    res = await _server().call_tool("get_company", {"id": "923609016"})
    assert res.is_error is False and res.structured_content["name"] == "EQUINOR ASA" and res.structured_content["raw"]["antallAnsatte"] == 21272


@pytest.mark.asyncio
@respx.mock
async def test_unknown_and_removed_entities_are_error_results():
    respx.get("https://data.brreg.no/enhetsregisteret/api/enheter/000000000").mock(return_value=httpx.Response(404))
    res = await _server().call_tool("get_company", {"id": "000000000"})
    assert res.is_error is True and res.structured_content["error"] == "not_found" and res.structured_content["http_status"] == 404
    respx.get("https://data.brreg.no/enhetsregisteret/api/enheter/111111111").mock(return_value=httpx.Response(410, json={"status": 410, "message": "Fjernet av juridiske årsaker"}))
    res = await _server().call_tool("get_company", {"id": "111111111"})
    assert res.is_error is True and res.structured_content["error"] == "not_found" and res.structured_content["http_status"] == 410
