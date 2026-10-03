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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "macro_collector.json").read_text(encoding="utf-8"))
BASE = "https://api.stlouisfed.org"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"api_key": "abcdefghijklmnopqrstuvwxyz123456"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_market_data_vocabulary():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_series", "me", "search_symbols"]
    gs = next(t for t in tools if t.name == "get_series")
    assert gs.annotations.read_only_hint is True and gs.input_schema["required"] == ["series_id"] and gs.meta["platform_mcp/endpoint"] == "/fred/series/observations"
    assert set(SPEC["adapter"]["not_offered"]) == {"get_candles", "get_news"}


@pytest.mark.asyncio
@respx.mock
async def test_get_series_maps_observations_and_sends_the_key_as_a_query_parameter():
    # fred.stlouisfed.org/docs/api/fred/series_observations.html example shape
    respx.get(f"{BASE}/fred/series/observations").mock(return_value=httpx.Response(200, json={
        "realtime_start": "2026-09-24", "realtime_end": "2026-09-24", "observation_start": "2026-01-01", "observation_end": "9999-12-31", "units": "lin", "output_type": 1,
        "file_type": "json", "order_by": "observation_date", "sort_order": "asc", "count": 2, "offset": 0, "limit": 100000,
        "observations": [{"realtime_start": "2026-09-24", "realtime_end": "2026-09-24", "date": "2026-01-01", "value": "4.33"},
                         {"realtime_start": "2026-09-24", "realtime_end": "2026-09-24", "date": "2026-02-01", "value": "."}]}))
    res = await _server().call_tool("get_series", {"series_id": "FEDFUNDS", "start": "2026-01-01"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["points"][0] == {"time": "2026-01-01", "value": "4.33", "raw": {"realtime_start": "2026-09-24", "realtime_end": "2026-09-24", "date": "2026-01-01", "value": "4.33"}}
    assert sc["points"][1]["value"] == "." and sc["total"] == 2 and sc["next_page"] is None
    q = respx.calls.last.request.url.params
    assert q["series_id"] == "FEDFUNDS" and q["observation_start"] == "2026-01-01" and q["file_type"] == "json" and q["api_key"] == "abcdefghijklmnopqrstuvwxyz123456"
    assert "observation_end" not in q and "Authorization" not in respx.calls.last.request.headers


@pytest.mark.asyncio
@respx.mock
async def test_search_symbols_maps_seriess():
    respx.get(f"{BASE}/fred/series/search").mock(return_value=httpx.Response(200, json={
        "realtime_start": "2017-08-01", "realtime_end": "2017-08-01", "order_by": "search_rank", "sort_order": "desc", "count": 32, "offset": 0, "limit": 1000,
        "seriess": [{"id": "MSIM2", "realtime_start": "2017-08-01", "realtime_end": "2017-08-01", "title": "Monetary Services Index: M2 (preferred)", "observation_start": "1967-01-01",
                     "observation_end": "2013-12-01", "frequency": "Monthly", "frequency_short": "M", "units": "Billions of Dollars", "units_short": "Bil. of $",
                     "seasonal_adjustment": "Seasonally Adjusted", "seasonal_adjustment_short": "SA", "last_updated": "2014-01-17 07:16:44-06", "popularity": 34}]}))
    res = await _server().call_tool("search_symbols", {"query": "monetary services index", "limit": 10, "page": 2})
    assert res.is_error is False
    r = res.structured_content["results"][0]
    assert r["symbol"] == "MSIM2" and r["name"] == "Monetary Services Index: M2 (preferred)" and r["type"] == "Monthly"
    assert res.structured_content["total"] == 32 and res.structured_content["next_page"] is None
    q = respx.calls.last.request.url.params
    assert q["search_text"] == "monetary services index" and q["limit"] == "10" and q["offset"] == "10" and q["file_type"] == "json"


@pytest.mark.asyncio
@respx.mock
async def test_bad_key_400_is_an_is_error_result():
    # live answer for a missing/invalid key (opened 2026-09-24)
    respx.get(f"{BASE}/fred/series").mock(return_value=httpx.Response(400, json={"error_code": 400, "error_message": "Bad Request.  Variable api_key is not set."}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 400
    assert "abcdefghijklmnopqrstuvwxyz123456" not in json.dumps(res.structured_content)
