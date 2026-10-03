import json
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402


def _form(req):
    return {k: v[0] for k, v in parse_qs(req.content.decode()).items()}


async def _names(server):
    return sorted(t.name for t in await server.list_tools())

SPEC = json.loads((ROOT / "catalog" / "ads" / "meta_audience_network.json").read_text(encoding="utf-8"))
G = "https://graph.facebook.com/v25.0"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"access_token": "EAANTOKEN"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["get_report", "me"]


@pytest.mark.asyncio
@respx.mock
async def test_report_query_and_rows_per_metric():
    route = respx.get(f"{G}/9876/adnetworkanalytics").mock(return_value=httpx.Response(200, json={"data": [{"query_id": "q1", "results": [
        {"time": "2026-09-01T07:00:00+0000", "metric": "fb_ad_network_imp", "breakdowns": [], "value": "1200"},
        {"time": "2026-09-01T07:00:00+0000", "metric": "fb_ad_network_revenue", "breakdowns": [], "value": "3.21"}]}]}))
    res = await _server().call_tool("get_report", {"account_id": "9876", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Bearer EAANTOKEN"
    p = req.url.params
    assert (p["since"], p["until"], p["aggregation_period"], p["limit"]) == ("2026-09-01", "2026-09-07", "day", "2000")
    assert json.loads(p["metrics"]) == ["fb_ad_network_request", "fb_ad_network_imp", "fb_ad_network_click", "fb_ad_network_revenue"]
    rows = res.structured_content["rows"]
    assert [(r["metric"], r["value"]) for r in rows] == [("fb_ad_network_imp", "1200"), ("fb_ad_network_revenue", "3.21")]


@pytest.mark.asyncio
@respx.mock
async def test_expired_token_is_auth_error_without_leak():
    respx.get(f"{G}/me").mock(return_value=httpx.Response(401, json={"error": {"message": "Error validating access token EAANTOKEN", "code": 190}}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["error"] == "auth_error" and "EAANTOKEN" not in json.dumps(res.structured_content)
