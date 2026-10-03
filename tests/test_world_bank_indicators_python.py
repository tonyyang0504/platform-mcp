"""World Bank Indicators (forge stress test 2026-10): [meta, rows] answers, 200 error arrays (fail_if_present through an
index), a two-dimensional series id split with part:."""
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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "world_bank_indicators.json").read_text(encoding="utf-8"))
BASE = "https://api.worldbank.org/v2"


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_series_split_and_window():
    route = respx.get(f"{BASE}/country/USA/indicator/NY.GDP.MKTP.CD").mock(return_value=httpx.Response(200, json=[
        {"page": 1, "pages": 1, "per_page": 20000, "total": 2},
        [{"date": "2024", "value": 29298013000000}, {"date": "2023", "value": None}]]))
    pts = (await _server().call_tool("get_series", {"series_id": "USA/NY.GDP.MKTP.CD", "start": "2023-01-01", "end": "2024-12-31"})).structured_content["points"]
    assert [(p["time"], p["value"]) for p in pts] == [("2024", 29298013000000), ("2023", None)]
    q = route.calls.last.request.url.params
    assert (q["format"], q["date"]) == ("json", "2023:2024")
    await _server().call_tool("get_series", {"series_id": "USA/NY.GDP.MKTP.CD", "start": "2023-01-01"})
    assert "date" not in route.calls.last.request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_error_array_and_missing_part():
    respx.get(f"{BASE}/country/USA/indicator/NOPE.X").mock(return_value=httpx.Response(200, json=[
        {"message": [{"id": "120", "key": "Invalid value", "value": "The provided parameter value is not valid"}]}]))
    r = await _server().call_tool("get_series", {"series_id": "USA/NOPE.X"})
    assert r.is_error and r.structured_content["error"] == "invalid_input" and r.structured_content["message"] == "The provided parameter value is not valid"
    r = await _server().call_tool("get_series", {"series_id": "USA"})
    assert r.is_error and r.structured_content["error"] == "invalid_input"
