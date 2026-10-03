"""Adapter tests for jobs/france_travail (respx-mocked; no network)."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "france_travail.json").read_text(encoding="utf-8"))
CREDS = {'client_id': 'ft-cid', 'client_secret': 'ft-SECRETvalue'}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope"))
    return build_server(SPEC, transport=t)


def _dig(obj, path):
    for part in path.split("."):
        obj = obj[int(part)] if isinstance(obj, list) else obj.get(part)
    return obj


def _mock_token():
    return respx.post('https://entreprise.francetravail.fr/connexion/oauth2/access_token').mock(return_value=httpx.Response(200, json={'access_token': 'FT-TOKEN-abc', 'token_type': 'Bearer', 'expires_in': 1499, 'scope': 'api_offresdemploiv2 o2dsoffre'}))


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ['get_posting', 'search']
    for t in tools:
        assert t.input_schema["additionalProperties"] is False and t.title
        assert t.annotations.read_only_hint in (True, False)


@pytest.mark.asyncio
@respx.mock
async def test_main_search_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='GET', url__startswith='https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search').mock(return_value=httpx.Response(206, json={'resultats': [{'id': '048KLTP', 'intitule': 'Développeur', 'entreprise': {'nom': 'ACME'}, 'lieuTravail': {'libelle': '75 - Paris'}, 'origineOffre': {'urlOrigine': 'https://candidat.francetravail.fr/offres/recherche/detail/048KLTP'}, 'dateCreation': '2026-09-20T10:00:00Z', 'description': 'Poste'}], 'filtresPossibles': []}))
    res = await _server().call_tool('search', {'query': 'informatique'})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'postings.0.id': '048KLTP', 'postings.0.company': 'ACME', 'postings.0.location': '75 - Paris', 'total': None}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search'
    assert req.url.params.get('motsCles') == 'informatique'
    assert 'range' not in req.url.params
    assert req.headers['Authorization'] == 'Bearer FT-TOKEN-abc'
    assert {k: v[0] for k, v in parse_qs(token.calls.last.request.content.decode()).items()} == {'grant_type': 'client_credentials', 'client_id': 'ft-cid', 'client_secret': 'ft-SECRETvalue', 'scope': 'api_offresdemploiv2 o2dsoffre'}


@pytest.mark.asyncio
@respx.mock
async def test_extra_get_posting_maps_documented_fields():
    token = _mock_token()
    route = respx.route(method='GET', url__startswith='https://api.francetravail.io/partenaire/offresdemploi/v2/offres/048KLTP').mock(return_value=httpx.Response(200, json={'id': '048KLTP', 'intitule': 'Développeur', 'description': 'Texte', 'dateCreation': '2026-09-20T10:00:00Z'}))
    res = await _server().call_tool('get_posting', {'id': '048KLTP'})
    assert res.is_error is False, res.structured_content
    sc = res.structured_content
    for path, want in {'id': '048KLTP', 'title': 'Développeur', 'description': 'Texte'}.items():
        assert _dig(sc, path) == want, (path, _dig(sc, path))
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == 'https://api.francetravail.io/partenaire/offresdemploi/v2/offres/048KLTP'


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_is_an_is_error_result_not_a_protocol_error():
    _mock_token()
    respx.route(method='GET', url__startswith='https://api.francetravail.io/partenaire/offresdemploi/v2/offres/X').mock(return_value=httpx.Response(429, headers={"Retry-After": "30"}))
    res = await _server().call_tool('get_posting', {'id': 'X'})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited" and res.structured_content["retry_after_seconds"] == 30


@pytest.mark.asyncio
@respx.mock
async def test_auth_failure_is_reported_without_leaking_the_secret():
    _mock_token()
    respx.route(method='GET', url__startswith='https://api.francetravail.io/partenaire/offresdemploi/v2/offres/X').mock(return_value=httpx.Response(401, json={"error": "bad credentials ft-SECRETvalue"}))
    res = await _server().call_tool('get_posting', {'id': 'X'})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert 'ft-SECRETvalue' not in json.dumps(res.structured_content)
