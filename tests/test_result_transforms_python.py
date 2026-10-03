"""Runtime result transforms added with the forge verification (columnar, slice + sort, fmt:, iso:,
fail_when/error_field paths through arrays, 'rate limit' wording). The TypeScript twin is
result_transforms.typescript.test.mjs; both assert the same outputs."""
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

BASE = "https://api.transforms.example"


def spec(tools: dict, envelope: dict | None = None) -> dict:
    a = {"base_url": BASE, "auth": {"type": "none"}, "rate_per_second": 50, "tools": tools}
    if envelope:
        a["envelope"] = envelope
    return {"id": "transforms", "category": "market_data", "docs_url": "https://x", "adapter": a}


def server(s: dict):
    a = s["adapter"]
    return build_server(s, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_columnar_rows_ragged_arrays_and_non_array_keys():
    respx.get(f"{BASE}/c").mock(return_value=httpx.Response(200, json={"s": "ok", "t": [1, 2, 3], "c": ["1.5", "2"]}))
    s = spec({"get_candles": {"path": "/c", "result": {"items": "$", "columnar": True, "key": "candles", "fields": {"time": "str:t", "open": "num:c", "high": "num:c", "low": "num:c", "close": "num:c"}}}})
    res = (await server(s).call_tool("get_candles", {"symbol": "X", "interval": "1h"})).structured_content
    assert [(c["time"], c["close"]) for c in res["candles"]] == [("1", 1.5), ("2", 2), ("3", None)]
    assert res["candles"][0]["raw"] == {"t": 1, "c": "1.5"}  # the scalar "s" is not a column


@pytest.mark.asyncio
@respx.mock
async def test_slice_sort_pages_and_caps_the_limit():
    rows = [{"code": c, "n": c.lower()} for c in ("D", "B", "A", "C", "E")]
    respx.get(f"{BASE}/all").mock(return_value=httpx.Response(200, json=rows))
    s = spec({"search_symbols": {"path": "/all", "max_limit": 2, "result": {"items": "$", "slice": True, "sort": "symbol", "key": "results", "fields": {"symbol": "code", "name": "n"}}}})
    p1 = (await server(s).call_tool("search_symbols", {"query": "x", "limit": 50})).structured_content
    assert [r["symbol"] for r in p1["results"]] == ["A", "B"] and p1["total"] == 5 and p1["next_page"] == 2  # limit capped at max_limit
    p3 = (await server(s).call_tool("search_symbols", {"query": "x", "limit": 2, "page": 3})).structured_content
    assert [r["symbol"] for r in p3["results"]] == ["E"] and p3["next_page"] is None
    p9 = (await server(s).call_tool("search_symbols", {"query": "x", "limit": 2, "page": 9})).structured_content
    assert p9["results"] == [] and p9["next_page"] is None


@pytest.mark.asyncio
@respx.mock
async def test_fmt_and_iso_result_fields():
    respx.get(f"{BASE}/n").mock(return_value=httpx.Response(200, json={"items": [
        {"id": 7, "slug": "a-b", "ts": 1438273200, "ms": 1438273200123, "iso": "2015-07-30T16:20:00Z"},
        {"id": 8, "ts": "1438273200", "ms": None, "iso": ""}]}))
    s = spec({"get_news": {"path": "/n", "result": {"items": "items", "key": "articles", "fields": {
        "id": "id", "title": "fmt:#{id} {slug}", "url": "fmt:https://site.example/p/{id}", "published_at": "iso:ts", "source": "iso:ms|iso"}}}})
    a = (await server(s).call_tool("get_news", {})).structured_content["articles"]
    assert a[0]["title"] == "#7 a-b" and a[0]["url"] == "https://site.example/p/7"
    assert a[0]["published_at"] == "2015-07-30T16:20:00Z" and a[0]["source"] == "2015-07-30T16:20:00Z"  # epoch ms detected
    assert a[1]["title"] is None and a[1]["url"] == "https://site.example/p/8"  # a missing part makes the whole string null
    assert a[1]["published_at"] == "2015-07-30T16:20:00Z" and a[1]["source"] is None


@pytest.mark.asyncio
@respx.mock
async def test_fail_when_reads_through_arrays_and_uses_a_dotted_error_field():
    respx.get(f"{BASE}/d/bad").mock(return_value=httpx.Response(200, json={"Results": [{"Make": "", "ErrorText": "6 - Incomplete VIN"}]}))
    respx.get(f"{BASE}/d/empty").mock(return_value=httpx.Response(200, json={"Results": [{"Make": ""}]}))
    s = spec({"get_series": {"path": "/d/{series_id}", "result": {"root": "Results.0", "fields": {"name": "Make"}}}},
             envelope={"fail_when": {"Results.0.Make": ""}, "error_field": "Results.0.ErrorText"})
    res = await server(s).call_tool("get_series", {"series_id": "bad"})
    assert res.is_error and res.structured_content["message"] == "6 - Incomplete VIN"
    res = await server(s).call_tool("get_series", {"series_id": "empty"})
    assert res.is_error and res.structured_content["message"] == ""  # no error text: the matched value is the message


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_wordings_in_a_200_envelope():
    for comment in ("Call limit exceeded", "Rate limit reached, slow down"):
        respx.get(f"{BASE}/e").mock(return_value=httpx.Response(200, json={"status": "FAILED", "comment": comment}))
        s = spec({"get_news": {"path": "/e", "result": {"items": "result", "key": "articles", "fields": {"id": "id"}}}},
                 envelope={"ok_field": "status", "ok_value": "OK", "error_field": "comment"})
        res = await server(s).call_tool("get_news", {})
        assert res.is_error and res.structured_content["error"] == "rate_limited", comment


@pytest.mark.asyncio
@respx.mock
async def test_arg_echoes_a_tool_argument_into_the_result():
    # Bitstamp's GET /api/v2/ticker/{pair}/ does not repeat the pair (found by the headless mcp-forge agent run)
    respx.get(f"{BASE}/ticker/btcusd/").mock(return_value=httpx.Response(200, json={"last": "84810.49", "bid": "84810", "ask": "84811"}))
    s = {"id": "transforms", "category": "trading", "docs_url": "https://x", "adapter": {"base_url": BASE, "auth": {"type": "none"}, "tools": {
        "get_ticker": {"path": "/ticker/{symbol}/", "result": {"fields": {"symbol": "arg:symbol", "last": "num:last", "bid": "num:bid", "ask": "num:ask"}}}}}}
    res = await server(s).call_tool("get_ticker", {"symbol": "btcusd"})
    assert res.is_error is False and res.structured_content["symbol"] == "btcusd" and res.structured_content["last"] == 84810.49
