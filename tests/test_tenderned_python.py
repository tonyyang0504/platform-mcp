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

SPEC = json.loads((ROOT / "catalog" / "deals" / "tenderned.json").read_text(encoding="utf-8"))
API = "https://www.tenderned.nl/papi/tenderned-rs-tns/v2"
ROW = {"publicatieId": "441637", "publicatieDatum": "2026-09-25", "aanbestedingNaam": "Senior specialist mechanische riolering",
       "opdrachtgeverNaam": "Gemeente Haarlemmermeer", "typePublicatie": {"code": "AGO"}, "opdrachtBeschrijving": "De komende jaren",
       "link": {"href": "https://www.tenderned.nl/aankondigingen/overzicht/441637", "title": "self"}}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test"))


@pytest.mark.asyncio
@respx.mock
async def test_list_is_keyless_and_zero_based():
    route = respx.get(f"{API}/publicaties").mock(return_value=httpx.Response(200, json={"content": [ROW], "totalElements": 145982, "number": 1, "size": 20}))
    server = _server()
    assert [t.name for t in await server.list_tools()] == ["search_postings"]
    res = await server.call_tool("search_postings", {"page": 2, "limit": 20})
    out = res.structured_content
    p = out["postings"][0]
    assert p["id"] == "441637" and p["buyer"] == "Gemeente Haarlemmermeer" and p["posted_at"] == "2026-09-25"
    assert p["url"] == "https://www.tenderned.nl/aankondigingen/overzicht/441637" and out["total"] == 145982
    q = route.calls.last.request.url.params
    assert q["page"] == "1" and q["size"] == "20"
    assert "authorization" not in route.calls.last.request.headers


@pytest.mark.asyncio
@respx.mock
async def test_limit_capped_and_errors():
    route = respx.get(f"{API}/publicaties").mock(return_value=httpx.Response(200, json={"content": [], "totalElements": 0}))
    res = await _server().call_tool("search_postings", {"limit": 100})
    assert res.structured_content["postings"] == [] and route.calls.last.request.url.params["page"] == "0"
    respx.get(f"{API}/publicaties").mock(return_value=httpx.Response(503, text="unavailable"))
    assert (await _server().call_tool("search_postings", {})).is_error is True
