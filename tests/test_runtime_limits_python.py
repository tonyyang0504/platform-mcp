"""Regression tests for the limits fixed after the forge verification (docs/FORGE_VERIFICATION.md):
the error-kind table and its per-entry overrides (adapter.error_kinds), the short-lived bounded response
cache for locally paged collections, result.filter on sliced feeds and page-only mapping.
The TypeScript twin is runtime_limits.typescript.test.mjs; both assert the same outputs."""
import asyncio
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.errors import classify  # noqa: E402
from platform_mcp_hub.http import ResponseCache, Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

BASE = "https://api.limits.example"
SECRET = "sk-live-0123456789abcdef"


def spec(tools: dict, category: str = "market_data", **adapter) -> dict:
    return {"id": "limits", "category": category, "docs_url": "https://x",
            "adapter": {"base_url": BASE, "auth": {"type": "bearer", "field": "token", "fields": [{"name": "token"}]}, "rate_per_second": 50, "tools": tools, **adapter}}


def server(s: dict, cache: ResponseCache | None = None):
    a = s["adapter"]
    t = Transport(a["base_url"], a["auth"], {"token": SECRET}, 50, "test", envelope=a.get("envelope"))
    if cache is not None:
        t.cache = cache
    return build_server(s, transport=t), t


SERIES = {"get_series": {"path": "/s/{series_id}", "result": {"root": "data", "fields": {"name": "n"}}}}
SEARCH = {"search_symbols": {"path": "/q", "params": {"q": "query"}, "result": {"items": "data", "key": "results", "fields": {"symbol": "s"}}}}

# (status, body, method, expected kind): the default table
TABLE = [
    (400, {"message": "Invalid parameter 'from': must be a date"}, "GET", "invalid_input"),
    (422, {"status": 422, "message": "invalid currency: XXXQ"}, "GET", "invalid_input"),
    (422, "Failed to deserialize the JSON body", "POST", "invalid_input"),
    (400, {"status": "FAILED", "comment": "contestId: Contest with id 99999999 not found"}, "GET", "not_found"),
    (400, {"error": "API key not valid. Please pass a valid API key."}, "GET", "auth_error"),
    (400, {"status": "FAILED", "comment": "Call limit exceeded"}, "GET", "rate_limited"),
    (400, {"oops": 1}, "GET", "upstream_error"),
    (401, {"error": "unauthorized"}, "GET", "auth_error"),
    (403, "forbidden", "GET", "auth_error"),
    (404, {"error": "no such series"}, "GET", "not_found"),
    (404, {"error": "no such order"}, "POST", "invalid_input"),
    (409, {"error": "version mismatch"}, "PUT", "conflict"),
    (410, "gone", "GET", "not_found"),
    (429, "slow down", "GET", "rate_limited"),
    (500, {"error": "invalid state"}, "GET", "upstream_error"),
    (502, "bad gateway", "GET", "upstream_error"),
    (503, "", "GET", "upstream_error"),
]


@pytest.mark.parametrize("status,body,method,kind", TABLE)
def test_classify_table(status, body, method, kind):
    import json
    text = body if isinstance(body, str) else json.dumps(body)
    assert classify(status, text, method=method).kind == kind


@pytest.mark.asyncio
@respx.mock
async def test_http_errors_through_a_tool_carry_the_kind_status_and_no_secret():
    s, _ = server(spec(SERIES))
    respx.get(f"{BASE}/s/a").mock(return_value=httpx.Response(400, json={"message": f"invalid series key; token {SECRET} ok"}))
    respx.get(f"{BASE}/s/b").mock(return_value=httpx.Response(404, json={"error": "unknown"}))
    respx.get(f"{BASE}/s/c").mock(return_value=httpx.Response(409, json={"error": "busy"}))
    respx.get(f"{BASE}/s/d").mock(return_value=httpx.Response(503, text="maintenance"))
    respx.get(f"{BASE}/s/e").mock(return_value=httpx.Response(429, headers={"Retry-After": "7"}, text="x"))
    got = {}
    for k in "abcde":
        r = await s.call_tool("get_series", {"series_id": k})
        assert r.is_error
        got[k] = r.structured_content
    assert (got["a"]["error"], got["a"]["http_status"]) == ("invalid_input", 400)
    assert SECRET not in got["a"]["message"] and "invalid series key" in got["a"]["message"]
    assert (got["b"]["error"], got["c"]["error"], got["d"]["error"]) == ("not_found", "conflict", "upstream_error")
    assert (got["e"]["error"], got["e"]["retry_after_seconds"]) == ("rate_limited", 7.0)


@pytest.mark.asyncio
@respx.mock
async def test_error_kinds_overrides_win_for_http_statuses_and_envelopes():
    rules = [{"status": 500, "match": "unknown symbol", "kind": "invalid_input"},  # a vendor answering bad input with 500
             {"status": 400, "kind": "upstream_error"},  # a vendor whose 400 means 'our side broke'
             {"status": 200, "match": "no data", "kind": "not_found"}]  # an envelope failure
    s, _ = server(spec(SERIES, error_kinds=rules, envelope={"ok_field": "ok", "error_field": "msg"}))
    respx.get(f"{BASE}/s/a").mock(return_value=httpx.Response(500, json={"msg": "Unknown symbol ZZZ"}))
    respx.get(f"{BASE}/s/b").mock(return_value=httpx.Response(400, json={"msg": "invalid parameter"}))
    respx.get(f"{BASE}/s/c").mock(return_value=httpx.Response(200, json={"ok": False, "msg": "No data for this key"}))
    respx.get(f"{BASE}/s/d").mock(return_value=httpx.Response(500, json={"msg": "db down"}))
    kinds = [(await s.call_tool("get_series", {"series_id": k})).structured_content["error"] for k in "abcd"]
    assert kinds == ["invalid_input", "upstream_error", "not_found", "upstream_error"]


@pytest.mark.asyncio
@respx.mock
async def test_empty_record_on_a_get_is_not_found():
    s, _ = server(spec(SERIES))
    respx.get(f"{BASE}/s/x").mock(return_value=httpx.Response(200, json={"data": {}}))
    r = await s.call_tool("get_series", {"series_id": "x"})
    assert (r.structured_content["error"], r.structured_content["http_status"]) == ("not_found", 404)


SLICED = {"search_symbols": {"path": "/all", "max_limit": 100, "result": {"items": "$", "slice": True, "key": "results", "fields": {"symbol": "s", "name": "n"}}}}
ROWS = [{"s": f"S{i:02d}", "n": f"name {i}"} for i in range(10)]


@pytest.mark.asyncio
@respx.mock
async def test_paging_a_sliced_collection_downloads_it_once_within_the_ttl():
    route = respx.get(f"{BASE}/all").mock(return_value=httpx.Response(200, json=ROWS))
    s, t = server(spec(SLICED))
    pages = [(await s.call_tool("search_symbols", {"query": "x", "limit": 4, "page": p})).structured_content for p in (1, 2, 3)]
    assert [[r["symbol"] for r in p["results"]] for p in pages] == [["S00", "S01", "S02", "S03"], ["S04", "S05", "S06", "S07"], ["S08", "S09"]]
    assert [p["next_page"] for p in pages] == [2, 3, None] and pages[0]["total"] == 10
    assert route.call_count == 1 and t.cache.hits == 2


@pytest.mark.asyncio
@respx.mock
async def test_cache_entries_expire_after_the_ttl():
    route = respx.get(f"{BASE}/all").mock(return_value=httpx.Response(200, json=ROWS))
    tools = {"search_symbols": {**SLICED["search_symbols"], "cache_ttl": 0.05}}
    s, _ = server(spec(tools))
    await s.call_tool("search_symbols", {"query": "x"})
    await asyncio.sleep(0.12)
    await s.call_tool("search_symbols", {"query": "x"})
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_cache_is_bounded_by_bytes_and_entries_and_skips_oversized_bodies():
    import json
    route = respx.get(url__regex=rf"{BASE}/all.*").mock(side_effect=lambda req: httpx.Response(200, json=ROWS))
    body = len(json.dumps(ROWS, separators=(",", ":")).encode())  # the bytes the platform sent
    tools = {"search_symbols": {**SLICED["search_symbols"], "params": {"q": "query"}}}
    s, t = server(spec(tools), cache=ResponseCache(max_bytes=body * 2, max_entries=8))
    for q in ("a", "b", "c"):  # three distinct requests, room for two
        await s.call_tool("search_symbols", {"query": q})
    assert len(t.cache.entries) == 2 and t.cache.bytes <= body * 2
    await s.call_tool("search_symbols", {"query": "a"})  # evicted (least recently used): fetched again
    assert route.call_count == 4
    s2, t2 = server(spec(tools), cache=ResponseCache(max_bytes=body - 1, max_entries=8))
    await s2.call_tool("search_symbols", {"query": "a"})
    await s2.call_tool("search_symbols", {"query": "a"})
    assert len(t2.cache.entries) == 0 and route.call_count == 6  # larger than the cap: never stored
    s3, t3 = server(spec(tools), cache=ResponseCache(max_bytes=10_000_000, max_entries=1))
    await s3.call_tool("search_symbols", {"query": "a"})
    await s3.call_tool("search_symbols", {"query": "b"})
    assert list(t3.cache.entries) and len(t3.cache.entries) == 1


@pytest.mark.asyncio
@respx.mock
async def test_cache_can_be_disabled_and_never_holds_failures_or_uncached_tools(monkeypatch):
    route = respx.get(f"{BASE}/all").mock(side_effect=[httpx.Response(200, json={"ok": False, "msg": "call limit exceeded"}), httpx.Response(200, json=ROWS), httpx.Response(200, json=ROWS)])
    s, _ = server(spec(SLICED, envelope={"ok_field": "ok", "error_field": "msg"}))
    r = await s.call_tool("search_symbols", {"query": "x"})  # a 200 envelope failure: not cached
    assert r.structured_content["error"] == "rate_limited"
    await s.call_tool("search_symbols", {"query": "x"})
    await s.call_tool("search_symbols", {"query": "x", "page": 2})
    assert route.call_count == 2
    plain = respx.get(f"{BASE}/q").mock(return_value=httpx.Response(200, json={"data": [{"s": "A"}]}))
    s2, _ = server(spec(SEARCH))
    await s2.call_tool("search_symbols", {"query": "a"})
    await s2.call_tool("search_symbols", {"query": "a"})
    assert plain.call_count == 2  # a server-paged tool is never cached
    monkeypatch.setenv("PLATFORM_MCP_CACHE_MAX_MB", "0")
    assert ResponseCache().enabled is False
    monkeypatch.setenv("PLATFORM_MCP_CACHE_MAX_MB", "64")
    monkeypatch.setenv("PLATFORM_MCP_CACHE_TTL", "0")
    allr = respx.get(f"{BASE}/all2").mock(return_value=httpx.Response(200, json=ROWS))
    s3, _ = server(spec({"search_symbols": {**SLICED["search_symbols"], "path": "/all2"}}))
    await s3.call_tool("search_symbols", {"query": "x"})
    await s3.call_tool("search_symbols", {"query": "x"})
    assert allr.call_count == 2  # TTL 0: caching off for sliced tools


FILTERED = {"discover": {"path": "/c", "max_limit": 100, "result": {"items": "result", "slice": True, "key": "competitions",
            "filter": [{"arg": "query", "fields": ["title"]}, {"arg": "kind", "fields": ["kind"], "match": "equals"},
                       {"arg": "status", "fields": ["status"], "match": "equals", "value": "map:status:open=CODING,upcoming=BEFORE,completed=FINISHED"}],
            "fields": {"id": "id", "title": "name", "kind": "=coding", "status": "phase"}}}}
CONTESTS = {"result": [{"id": 1, "name": "Round 1 (Div. 2)", "phase": "FINISHED"}, {"id": 2, "name": "Educational Round", "phase": "BEFORE"},
                       {"id": 3, "name": "Round 3 (Div. 1)", "phase": "CODING"}, {"id": 4, "name": "Global Round", "phase": "FINISHED"}]}


@pytest.mark.asyncio
@respx.mock
async def test_filters_apply_to_sliced_feeds_before_paging():
    respx.get(f"{BASE}/c").mock(return_value=httpx.Response(200, json=CONTESTS))
    s, _ = server(spec(FILTERED, category="competitions"))

    async def ids(args):
        r = (await s.call_tool("discover", args)).structured_content
        return [c["id"] for c in r["competitions"]], r["total"], r["next_page"]
    assert await ids({"query": "round"}) == (["1", "2", "3", "4"], 4, None)
    assert await ids({"query": "DIV."}) == (["1", "3"], 2, None)
    assert await ids({"status": "completed"}) == (["1", "4"], 2, None)
    assert await ids({"status": "upcoming", "query": "round"}) == (["2"], 1, None)
    assert await ids({"kind": "design"}) == ([], 0, None)
    assert await ids({"query": "round", "limit": 3, "page": 1}) == (["1", "2", "3"], 4, 2)
    bad = await s.call_tool("discover", {"status": "someday"})
    assert bad.is_error and bad.structured_content["error"] == "invalid_input"


@pytest.mark.asyncio
@respx.mock
async def test_page_only_mapping_gives_the_same_page_as_mapping_everything():
    respx.get(f"{BASE}/all").mock(return_value=httpx.Response(200, json=ROWS + ["not a record", 7]))
    s, _ = server(spec(SLICED))
    r = (await s.call_tool("search_symbols", {"query": "x", "limit": 3, "page": 4})).structured_content
    assert [x["symbol"] for x in r["results"]] == ["S09"] and r["total"] == 10 and r["next_page"] is None
    assert r["results"][0]["raw"] == {"s": "S09", "n": "name 9"}
