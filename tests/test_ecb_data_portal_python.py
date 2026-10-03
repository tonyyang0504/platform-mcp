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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "ecb_data_portal.json").read_text(encoding="utf-8"))
URL = "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A"
XML = (ROOT / "tests" / "fixtures" / "live" / "ecb_exr_usd.xml").read_text(encoding="utf-8")


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
async def test_get_series_only():
    assert [t.name for t in await _server().list_tools()] == ["get_series"]


@pytest.mark.asyncio
@respx.mock
async def test_sdmx_generic_xml_is_parsed_into_points():
    route = respx.get(URL).mock(return_value=httpx.Response(200, text=XML, headers={"content-type": "application/vnd.sdmx.genericdata+xml;version=2.1"}))
    res = await _server().call_tool("get_series", {"series_id": "EXR/D.USD.EUR.SP00.A", "start": "2026-09-01", "end": "2026-09-04"})
    assert res.is_error is False
    assert [(p["time"], p["value"]) for p in res.structured_content["points"]] == [("2026-09-01", 1.159), ("2026-09-02", 1.1578), ("2026-09-03", 1.1615), ("2026-09-04", 1.1622)]
    req = route.calls.last.request
    # the API content-negotiates: without this Accept it answers SDMX-JSON, which the mapping cannot read
    assert req.headers["Accept"] == "application/vnd.sdmx.genericdata+xml;version=2.1"
    assert req.url.params["startPeriod"] == "2026-09-01" and req.url.params["endPeriod"] == "2026-09-04" and req.url.params["detail"] == "dataonly"


@pytest.mark.asyncio
@respx.mock
async def test_unknown_series_is_not_found():
    respx.get("https://data-api.ecb.europa.eu/service/data/EXR/D.ZZZ.EUR.SP00.A").mock(return_value=httpx.Response(404, text="No results found."))
    res = await _server().call_tool("get_series", {"series_id": "EXR/D.ZZZ.EUR.SP00.A"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"
