"""CNB exchange-rate fixing (forge stress test 2026-10, Czech docs): pipe-separated text/plain parsed with the tool's
`csv` option, DD.MM.YYYY dates (isodate:) and decimal commas (num_comma:), a column chosen by {series_id}."""
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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "cnb_fx.json").read_text(encoding="utf-8"))
URL = SPEC["adapter"]["base_url"] + "/rok.txt"
TEXT = ("Datum|1 AUD|1 EUR|100 JPY|1 USD\n02.01.2026|13,797|24,170|13,141|20,611\n05.01.2026|13,835|24,195|13,226|20,742\n"
        "Datum|1 AUD|1 EUR|100 JPY|1 USD|1 ZAR\n06.01.2026|13,900|24,200|13,300|20,800|1,250\n")


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_pipe_text_decimal_comma_dates():
    route = respx.get(URL).mock(return_value=httpx.Response(200, headers={"content-type": "text/plain;charset=UTF-8"}, text=TEXT))
    pts = (await _server().call_tool("get_series", {"series_id": "100 JPY", "start": "2026-01-01"})).structured_content["points"]
    assert [(p["time"], p["value"]) for p in pts] == [("2026-01-02", 13.141), ("2026-01-05", 13.226), ("2026-01-06", 13.3)]
    assert route.calls.last.request.url.params["rok"] == "2026"


@pytest.mark.asyncio
@respx.mock
async def test_unknown_column_gives_no_points():
    respx.get(URL).mock(return_value=httpx.Response(200, headers={"content-type": "text/plain"}, text=TEXT))
    r = (await _server().call_tool("get_series", {"series_id": "1 NOPE"})).structured_content
    assert r["points"] == []
