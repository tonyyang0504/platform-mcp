"""Bank of Canada Valet (forge stress test 2026-10, OpenAPI YAML in English and French): observations keyed by the
requested series name ({series_id} in a result path), series list keyed by name (items_are_values)."""
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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "bank_of_canada_valet.json").read_text(encoding="utf-8"))
BASE = "https://www.bankofcanada.ca/valet"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_observations_keyed_by_series():
    route = respx.get(f"{BASE}/observations/FXUSDCAD/json").mock(return_value=httpx.Response(200, json={
        "seriesDetail": {"FXUSDCAD": {"label": "USD/CAD"}}, "observations": [{"d": "2026-09-25", "FXUSDCAD": {"v": "1.4145"}}, {"d": "2026-09-26", "FXUSDCAD": {"v": "1.4160"}}]}))
    pts = (await _server().call_tool("get_series", {"series_id": "FXUSDCAD", "start": "2026-09-25"})).structured_content["points"]
    assert [(p["time"], p["value"]) for p in pts] == [("2026-09-25", 1.4145), ("2026-09-26", 1.416)]
    assert route.calls.last.request.url.params["start_date"] == "2026-09-25" and "end_date" not in route.calls.last.request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_series_list_and_unknown_series():
    respx.get(f"{BASE}/lists/series/json").mock(return_value=httpx.Response(200, json={"series": {
        "FXUSDCAD": {"label": "USD/CAD", "description": "Daily average exchange rate of the US dollar in Canadian dollars."},
        "A.AGRI": {"label": "Annual BCPI Agriculture", "description": "Annual commodity price index"}}}))
    r = (await _server().call_tool("search_symbols", {"query": "us dollar"})).structured_content
    assert [x["symbol"] for x in r["results"]] == ["FXUSDCAD"] and r["results"][0]["name"] == "USD/CAD"
    respx.get(f"{BASE}/observations/NOPEX/json").mock(return_value=httpx.Response(404, json={"message": "Series NOPEX not found."}))
    bad = await _server().call_tool("get_series", {"series_id": "NOPEX"})
    assert bad.is_error and bad.structured_content["error"] == "not_found"
