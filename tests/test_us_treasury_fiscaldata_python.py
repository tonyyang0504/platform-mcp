"""U.S. Treasury Fiscal Data (forge stress test 2026-10): one `filter` parameter built with fmt: optional groups."""
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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "us_treasury_fiscaldata.json").read_text(encoding="utf-8"))
URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/avg_interest_rates"
ROWS = {"data": [{"record_date": "2026-07-31", "security_desc": "Treasury Bills", "avg_interest_rate_amt": "3.758"},
                 {"record_date": "2026-08-31", "security_desc": "Treasury Bills", "avg_interest_rate_amt": "3.788"}], "meta": {"total-count": 2}}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_series_with_and_without_window():
    route = respx.get(URL).mock(return_value=httpx.Response(200, json=ROWS))
    pts = (await _server().call_tool("get_series", {"series_id": "Treasury Bills", "start": "2026-07-01"})).structured_content["points"]
    assert [(p["time"], p["value"]) for p in pts] == [("2026-07-31", 3.758), ("2026-08-31", 3.788)]
    q = route.calls.last.request.url.params
    assert q["filter"] == "security_desc:eq:Treasury Bills,record_date:gte:2026-07-01" and q["page[size]"] == "10000" and q["sort"] == "record_date"
    await _server().call_tool("get_series", {"series_id": "Treasury Bills"})
    assert route.calls.last.request.url.params["filter"] == "security_desc:eq:Treasury Bills"
    await _server().call_tool("get_series", {"series_id": "Treasury Bills", "end": "2026-08-31"})
    assert route.calls.last.request.url.params["filter"] == "security_desc:eq:Treasury Bills,record_date:lte:2026-08-31"


@pytest.mark.asyncio
@respx.mock
async def test_bad_date_is_refused_before_sending():
    route = respx.get(URL).mock(return_value=httpx.Response(200, json=ROWS))
    r = await _server().call_tool("get_series", {"series_id": "Treasury Bills", "start": "2026-07-01,security_desc:eq:x"})
    assert r.is_error and r.structured_content["error"] == "invalid_input" and not route.called
