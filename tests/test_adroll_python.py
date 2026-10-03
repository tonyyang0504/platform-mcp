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

SPEC = json.loads((ROOT / "catalog" / "ads" / "adroll.json").read_text(encoding="utf-8"))
A = "https://services.adroll.com"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"token": "patTOKEN123", "client_id": "APPKEY"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["get_report", "list_accounts", "list_campaigns", "me", "pause_resume"]


@pytest.mark.asyncio
@respx.mock
async def test_pat_header_and_apikey_query_on_campaign_list():
    route = respx.get(f"{A}/api/v1/advertisable/get_campaigns").mock(return_value=httpx.Response(200, json={"results": [
        {"eid": "CYTQ", "name": "Retargeting", "status": "approved", "budget": 350.0, "start_date": "2026-01-01", "end_date": None, "ui_budget_daily": True}]}))
    res = await _server().call_tool("list_campaigns", {"account_id": "ADV1"})
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Token patTOKEN123"
    assert dict(req.url.params) == {"advertisable": "ADV1", "apikey": "APPKEY"}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["name"], c["budget"]) == ("CYTQ", "Retargeting", 350.0)


@pytest.mark.asyncio
@respx.mock
async def test_pause_resume_maps_to_pause_and_unpause_paths():
    pause = respx.put(f"{A}/api/v1/campaign/pause").mock(return_value=httpx.Response(200, json={"results": "paused"}))
    unpause = respx.put(f"{A}/api/v1/campaign/unpause").mock(return_value=httpx.Response(200, json={"results": "approved"}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "CYTQ", "action": "pause"})
    assert res.structured_content["status"] == "paused" and pause.calls[0].request.url.params["campaign"] == "CYTQ"
    res = await _server().call_tool("pause_resume", {"campaign_id": "CYTQ", "action": "resume"})
    assert res.structured_content["status"] == "approved" and unpause.called


@pytest.mark.asyncio
@respx.mock
async def test_report_entity_format_and_auth_error_without_token_leak():
    route = respx.get(f"{A}/api/v1/report/campaign").mock(return_value=httpx.Response(200, json={"results": [{"campaign": "My campaign 1", "eid": "CYTQ", "cost": 500.0, "impressions": 213675, "clicks": 500}]}))
    res = await _server().call_tool("get_report", {"account_id": "ADV1", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert dict(route.calls[0].request.url.params) == {"advertisables": "ADV1", "start_date": "2026-09-01", "end_date": "2026-09-07", "data_format": "entity", "apikey": "APPKEY"}
    assert res.structured_content["rows"][0]["spend"] == 500.0
    respx.get(f"{A}/api/v1/organization/get").mock(return_value=httpx.Response(401, text="bad token patTOKEN123"))
    bad = await _server().call_tool("me", {})
    assert bad.structured_content["error"] == "auth_error" and "patTOKEN123" not in json.dumps(bad.structured_content)
