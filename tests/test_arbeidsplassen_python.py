"""Arbeidsplassen (NAV job vacancy feed): Bearer JWT, newest feed page as search, /api/v1/feedentry/{id} as get_posting."""
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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "arbeidsplassen.json").read_text(encoding="utf-8"))
BASE = "https://pam-stilling-feed.nav.no"
UUID = "9f47616c-718f-484a-8c77-4db72302d8b9"
LINE = {"id": UUID, "url": f"/api/v1/feedentry/{UUID}", "title": "Veterinærpatolog", "content_text": "Stillingsannonse", "date_modified": "2026-09-24T14:55:33.107613+02:00",
        "_feed_entry": {"uuid": UUID, "status": "ACTIVE", "title": "Veterinærpatolog", "businessName": "Veterinærinstituttet", "municipal": "ÅS", "sistEndret": "2026-09-24T14:55:33.107613+02:00"}}
ENTRY = {"uuid": UUID, "status": "ACTIVE", "sistEndret": "2026-09-24T14:55:27.503+02:00", "ad_content": {
    "uuid": UUID, "published": "2026-09-24T00:00:00+02:00", "expires": "2026-10-11T00:00:00+02:00", "title": "Veterinærpatolog", "description": "<h2>Om stillingen</h2><p>...</p>",
    "workLocations": [{"country": "NORGE", "address": "Elizabeth Stephansens v.1", "city": "ÅS", "postalCode": "1431", "county": "AKERSHUS", "municipal": "ÅS"}],
    "sourceurl": "https://jobbnorge.no/ledige-stillinger/stilling/300870", "applicationUrl": "https://jobseeker.jobbnorge.no/apply/300870", "applicationDue": "2026-10-11T00:00:00",
    "link": f"https://arbeidsplassen.nav.no/stillinger/stilling/{UUID}", "employer": {"name": "Veterinærinstituttet", "orgnr": None, "homepage": "https://www.vetinst.no/"},
    "engagementtype": "Fast", "extent": "Heltid"}}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"token": "JWT.PUBLIC.TOKEN"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary_and_carry_annotations():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search"]
    search = next(t for t in tools if t.name == "search")
    assert search.annotations.read_only_hint is True and search.annotations.destructive_hint is False
    assert search.input_schema["required"] == ["query"] and search.meta["platform_mcp/docs"] == "https://pam-stilling-feed.nav.no/swagger"
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_reads_the_newest_feed_page_with_the_bearer_token_and_sends_no_query():
    respx.get(f"{BASE}/api/v1/feed").mock(return_value=httpx.Response(200, json={"version": "1.0", "title": "Stillingsfeeden fra arbeidsplassen.no", "id": "906c38d3", "next_url": None, "next_id": None, "items": [LINE]}))
    res = await _server().call_tool("search", {"query": "veterinær", "location": "Ås", "page": 2, "limit": 5})
    assert res.is_error is False
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == UUID and p["title"] == "Veterinærpatolog" and p["company"] == "Veterinærinstituttet" and p["location"] == "ÅS"
    assert p["posted_at"] == "2026-09-24T14:55:33.107613+02:00" and "url" not in p and p["raw"]["_feed_entry"]["status"] == "ACTIVE"
    assert sc["total"] is None and sc["next_page"] is None
    req = respx.calls.last.request
    assert req.headers["Authorization"] == "Bearer JWT.PUBLIC.TOKEN"
    assert dict(req.url.params) == {"last": "true"}  # the feed has no search, page or limit parameters


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_maps_the_ad_content_of_a_feed_entry():
    respx.get(f"{BASE}/api/v1/feedentry/{UUID}").mock(return_value=httpx.Response(200, json=ENTRY))
    res = await _server().call_tool("get_posting", {"id": UUID})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == UUID and sc["title"] == "Veterinærpatolog" and sc["company"] == "Veterinærinstituttet" and sc["location"] == "ÅS"
    assert sc["url"] == f"https://arbeidsplassen.nav.no/stillinger/stilling/{UUID}" and sc["posted_at"] == "2026-09-24T00:00:00+02:00"
    assert sc["description"].startswith("<h2>Om stillingen</h2>") and sc["raw"]["applicationUrl"] == "https://jobseeker.jobbnorge.no/apply/300870"


@pytest.mark.asyncio
@respx.mock
async def test_expired_token_is_an_auth_error_result_without_echoing_the_token():
    respx.get(f"{BASE}/api/v1/feed").mock(return_value=httpx.Response(401, json={"error": "Unauthorized"}))
    res = await _server().call_tool("search", {"query": "x"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 401
    assert "JWT.PUBLIC.TOKEN" not in json.dumps(res.structured_content)
