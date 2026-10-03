"""Prozorro (forge stress test 2026-10, Ukrainian docs): an opaque `offset` token as the cursor, feed rows without
titles (opt_fields silently reduced), a 404 error envelope."""
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

SPEC = json.loads((ROOT / "catalog" / "deals" / "prozorro.json").read_text(encoding="utf-8"))
BASE = "https://public-api.prozorro.gov.ua/api/2.5"
ROW = {"id": "ca3fbd4f58f04aeb8298a7053be30664", "tenderID": "UA-2026-09-11-013413-a", "status": "active.awarded", "dateModified": "2026-10-01T16:32:51+03:00",
       "procuringEntity": {"name": "Академія патрульної поліції"}, "tenderPeriod": {"startDate": "2026-09-11T17:31:09+03:00", "endDate": "2026-09-28T17:33:16+03:00"}}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_feed_cursor_and_titles():
    route = respx.get(f"{BASE}/tenders").mock(return_value=httpx.Response(200, json={"data": [ROW], "next_page": {"offset": "1790861577.929.1.2ccf"}}))
    r = (await _server().call_tool("search_postings", {"limit": 1})).structured_content
    p = r["postings"][0]
    assert (p["title"], p["buyer"], p["url"], p["deadline"]) == ("UA-2026-09-11-013413-a", "Академія патрульної поліції", "https://prozorro.gov.ua/tender/UA-2026-09-11-013413-a", "2026-09-28T17:33:16+03:00")
    assert r["next_cursor"] == "1790861577.929.1.2ccf" and r["next_page"] is None
    await _server().call_tool("search_postings", {"limit": 1, "cursor": "1790861577.929.1.2ccf"})
    q = route.calls.last.request.url.params
    assert (q["offset"], q["descending"], q["limit"]) == ("1790861577.929.1.2ccf", "1", "1")


@pytest.mark.asyncio
@respx.mock
async def test_detail_and_unknown():
    respx.get(f"{BASE}/tenders/{ROW['id']}").mock(return_value=httpx.Response(200, json={"data": {**ROW, "title": "Послуги з організації харчування", "value": {"amount": 2405685.0, "currency": "UAH"}, "date": "2026-10-01T16:32:51+03:00"}}))
    t = (await _server().call_tool("get_posting", {"id": ROW["id"]})).structured_content
    assert (t["title"], t["budget_max"], t["currency"]) == ("Послуги з організації харчування", 2405685.0, "UAH")
    respx.get(f"{BASE}/tenders/nope").mock(return_value=httpx.Response(404, json={"status": "error", "errors": [{"location": "url", "name": "tender_id", "description": "Not Found"}]}))
    r = await _server().call_tool("get_posting", {"id": "nope"})
    assert r.is_error and r.structured_content["error"] == "not_found"
