"""Arbeitsagentur Jobsuche: fixed public X-API-Key, /pc/v6/jobs search, /pc/v4/jobdetails/{base64(refnr)}."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "arbeitsagentur.json").read_text(encoding="utf-8"))
BASE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
HIT = {"stellenangebotsart": "ARBEIT", "stellenangebotsTitel": "Softwareentwickler Python/C# (m/w/d)", "verguetungsangabe": "JAHRESGEHALT",
       "gehaltsspanneVon": 50000.0, "gehaltsspanneBis": 60000.0, "stellenlokationen": [{"adresse": {"plz": "88046", "ort": "Friedrichshafen", "region": "BADEN_WUERTTEMBERG", "land": "DEUTSCHLAND"}}],
       "datumErsteVeroeffentlichung": "2026-09-07", "hauptberuf": "Softwareentwickler/in", "firma": "FERCHAU GmbH", "arbeitgeberKundennummerHash": "IEmR=", "referenznummer": "12265-271357_JB5240730-S"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "jobboerse-jobsuche"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search"]  # no account endpoint: me / apply / list_messages are not offered
    search = next(t for t in tools if t.name == "search")
    assert search.annotations.read_only_hint is True and search.annotations.destructive_hint is False
    assert search.input_schema["required"] == ["query"] and search.meta["platform_mcp/endpoint"] == "/pc/v6/jobs"
    assert search.meta["platform_mcp/docs"] == "https://jobsuche.api.bund.dev/"
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_the_public_client_id_header_and_maps_v6_fields():
    respx.get(f"{BASE}/pc/v6/jobs").mock(return_value=httpx.Response(200, json={"ergebnisliste": [HIT], "maxErgebnisse": 2865, "page": 1, "size": 1}))
    res = await _server().call_tool("search", {"query": "python", "location": "Berlin", "page": 2, "limit": 50})
    assert res.is_error is False
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == "12265-271357_JB5240730-S" and p["title"] == "Softwareentwickler Python/C# (m/w/d)" and p["company"] == "FERCHAU GmbH"
    assert p["location"] == "Friedrichshafen" and p["posted_at"] == "2026-09-07" and p["salary_min"] == 50000.0 and p["salary_max"] == 60000.0
    assert "url" not in p and p["raw"]["hauptberuf"] == "Softwareentwickler/in"
    assert sc["total"] == 2865 and sc["next_page"] is None  # one hit on a page of 50
    req = respx.calls.last.request
    assert req.headers["X-API-Key"] == "jobboerse-jobsuche"
    assert req.url.params["was"] == "python" and req.url.params["wo"] == "Berlin" and req.url.params["page"] == "2" and req.url.params["size"] == "50"


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_takes_the_base64_refnr_and_maps_the_description():
    route = respx.get(f"{BASE}/pc/v4/jobdetails/MTIyNjUtMjcxMzU3X0pCNTI0MDczMC1T").mock(
        return_value=httpx.Response(200, json={**HIT, "stellenangebotsBeschreibung": "Die besten Köpfe ...", "istBetreut": False}))
    res = await _server().call_tool("get_posting", {"id": "MTIyNjUtMjcxMzU3X0pCNTI0MDczMC1T"})
    assert res.is_error is False and route.called
    sc = res.structured_content
    assert sc["id"] == "12265-271357_JB5240730-S" and sc["title"].startswith("Softwareentwickler") and sc["description"] == "Die besten Köpfe ..."
    assert sc["location"] == "Friedrichshafen" and sc["raw"]["arbeitgeberKundennummerHash"] == "IEmR="


@pytest.mark.asyncio
@respx.mock
async def test_refused_client_id_is_an_auth_error_result():
    respx.get(f"{BASE}/pc/v6/jobs").mock(return_value=httpx.Response(403, text="Forbidden"))
    res = await _server().call_tool("search", {"query": "python"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 403
