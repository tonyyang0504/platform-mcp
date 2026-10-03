import base64
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ads" / "impact_com.json").read_text(encoding="utf-8"))
B = "https://api.impact.com/Advertisers/IRabc123"


def _server(report_id="adv_perf_by_day"):
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"account_sid": "IRabc123", "auth_token": "imp-auth-secret", "report_id": report_id}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "list_campaigns", "get_report"}


@pytest.mark.asyncio
@respx.mock
async def test_list_campaigns_basic_auth_sid_in_path_and_state_filter():
    route = respx.get(f"{B}/Campaigns").mock(return_value=httpx.Response(200, json={"Campaigns": [{"Id": 1234, "Name": "US Program", "State": "ACTIVE", "Type": "Performance"}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "x", "status": "ACTIVE"})
    assert res.is_error is False
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Basic " + base64.b64encode(b"IRabc123:imp-auth-secret").decode()
    assert req.headers["Accept"] == "application/json"
    assert parse_qs(urlparse(str(req.url)).query) == {"State": ["ACTIVE"]}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["name"], c["status"]) == ("1234", "US Program", "ACTIVE")


@pytest.mark.asyncio
@respx.mock
async def test_get_report_runs_configured_report():
    route = respx.get(f"{B}/Reports/adv_perf_by_day").mock(return_value=httpx.Response(200, json={"Records": [{"Date": "2026-09-01", "Clicks": "10", "Actions": "2"}]}))
    res = await _server().call_tool("get_report", {"account_id": "x", "campaign_id": "1234", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    q = {k: v[0] for k, v in parse_qs(urlparse(str(route.calls[0].request.url)).query).items()}
    assert q == {"StartDate": "2026-09-01", "EndDate": "2026-09-07", "SUBAID": "1234"}
    assert res.structured_content["rows"][0]["raw"]["Clicks"] == "10"


@pytest.mark.asyncio
@respx.mock
async def test_missing_report_id_and_refused_token():
    bad = await _server(report_id=None).call_tool("get_report", {"account_id": "x", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert bad.is_error is True and bad.structured_content["error"] == "invalid_input"
    respx.get(f"{B}/CompanyInformation").mock(return_value=httpx.Response(401, text="bad token imp-auth-secret"))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "imp-auth-secret" not in json.dumps(res.structured_content)
