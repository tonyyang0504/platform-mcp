"""Swiss National Bank data portal (forge stress test 2026-10): a BOM + three-line preamble, semicolon CSV in long
format; one series picked by filters on a verb that does not page."""
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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "snb_data.json").read_text(encoding="utf-8"))
URL = "https://data.snb.ch/api/cube/devkum/data/csv/en"
CSV = ('﻿"CubeId";"devkum"\r\n"PublishingDate";"2026-10-01 14:30"\r\n\r\n"Date";"D0";"D1";"Value"\r\n'
       '"2026-08";"M0";"EUR1";"0.93629"\r\n"2026-08";"M0";"GBP1";"1.09363"\r\n"2026-08";"M1";"EUR1";"0.9301"\r\n"2026-09";"M0";"EUR1";\r\n"2026-09";"M0";"GBP1";"1.1"\r\n')


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_long_format_csv_filtered_to_one_series():
    route = respx.get(URL).mock(return_value=httpx.Response(200, headers={"content-type": "text/csv;charset=UTF-8"}, content=CSV.encode("utf-8")))
    pts = (await _server().call_tool("get_series", {"series_id": "devkum/M0/EUR1", "start": "2026-08-01"})).structured_content["points"]
    assert [(p["time"], p["value"]) for p in pts] == [("2026-08", 0.93629)]
    assert route.calls.last.request.url.params["fromDate"] == "2026-08"
    pts = (await _server().call_tool("get_series", {"series_id": "devkum/M0/GBP1"})).structured_content["points"]
    assert [p["value"] for p in pts] == [1.09363, 1.1]


@pytest.mark.asyncio
@respx.mock
async def test_unknown_cube():
    respx.get("https://data.snb.ch/api/cube/nope/data/csv/en").mock(return_value=httpx.Response(404, json={"code": "404", "message": "Table nope not found"}))
    r = await _server().call_tool("get_series", {"series_id": "nope/M0/EUR1"})
    assert r.is_error and r.structured_content["error"] == "not_found"
