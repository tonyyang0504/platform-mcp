"""Narodowy Bank Polski (forge stress test 2026-10, Polish docs): a date window in the path (path_params fmt:),
plain-text errors, table A list with Polish names."""
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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "nbp_rates.json").read_text(encoding="utf-8"))
BASE = "https://api.nbp.pl/api"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_series_window_in_path():
    route = respx.get(f"{BASE}/exchangerates/rates/A/USD/2026-09-25/2026-09-30/").mock(return_value=httpx.Response(200, json={
        "table": "A", "code": "USD", "rates": [{"no": "187/A/NBP/2026", "effectiveDate": "2026-09-25", "mid": 3.8404}]}))
    pts = (await _server().call_tool("get_series", {"series_id": "A/USD", "start": "2026-09-25", "end": "2026-09-30"})).structured_content["points"]
    assert [(p["time"], p["value"]) for p in pts] == [("2026-09-25", 3.8404)] and route.calls.last.request.url.params["format"] == "json"
    r = await _server().call_tool("get_series", {"series_id": "A/USD"})
    assert r.is_error and r.structured_content["error"] == "invalid_input" and "date:start" in r.structured_content["message"]


@pytest.mark.asyncio
@respx.mock
async def test_table_and_plain_text_errors():
    respx.get(f"{BASE}/exchangerates/tables/A/").mock(return_value=httpx.Response(200, json=[{"table": "A", "rates": [
        {"currency": "dolar amerykański", "code": "USD", "mid": 3.87}, {"currency": "euro", "code": "EUR", "mid": 4.2}]}]))
    r = (await _server().call_tool("search_symbols", {"query": "dolar"})).structured_content
    assert [x["symbol"] for x in r["results"]] == ["A/USD"] and r["results"][0]["name"] == "dolar amerykański"
    respx.get(f"{BASE}/exchangerates/rates/A/XXX/2026-09-25/2026-09-30/").mock(return_value=httpx.Response(404, text="404 NotFound - Not Found - Brak danych"))
    bad = await _server().call_tool("get_series", {"series_id": "A/XXX", "start": "2026-09-25", "end": "2026-09-30"})
    assert bad.is_error and bad.structured_content["error"] == "not_found"
