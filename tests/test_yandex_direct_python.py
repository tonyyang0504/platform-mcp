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

SPEC = json.loads((ROOT / "catalog" / "ads" / "yandex_direct.json").read_text(encoding="utf-8"))
A = "https://api.direct.yandex.com/json/v5"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"token": "y0_yandextoken", "client_login": "client-login"}, 50, "test", envelope=SPEC["adapter"]["envelope"])
    s = build_server(SPEC, transport=t)
    t.fixed_headers = SPEC["adapter"]["headers"]
    return s


@pytest.mark.asyncio
async def test_tool_list():
    assert await _names(_server()) == ["list_accounts", "list_campaigns", "me", "pause_resume"]


@pytest.mark.asyncio
@respx.mock
async def test_campaigns_get_body_headers_and_micros():
    route = respx.post(f"{A}/campaigns").mock(return_value=httpx.Response(200, json={"result": {"Campaigns": [
        {"Id": 101, "Name": "Search RU", "State": "ON", "Status": "ACCEPTED", "Currency": "RUB", "DailyBudget": {"Amount": 500000000, "Mode": "STANDARD"}, "StartDate": "2026-09-01"}]}}))
    res = await _server().call_tool("list_campaigns", {"account_id": "x", "status": "ON", "limit": 10, "page": 3})
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Bearer y0_yandextoken" and req.headers["Client-Login"] == "client-login"
    assert json.loads(req.content) == {"method": "get", "params": {"SelectionCriteria": {"States": ["ON"]}, "FieldNames": ["Id", "Name", "State", "Status", "Currency", "DailyBudget", "StartDate", "EndDate"], "Page": {"Limit": 10, "Offset": 20}}}
    c = res.structured_content["campaigns"][0]
    assert (c["id"], c["status"], c["currency"], c["budget_micros"]) == ("101", "ON", "RUB", 500000000)


@pytest.mark.asyncio
@respx.mock
async def test_suspend_and_resume_methods():
    route = respx.post(f"{A}/campaigns").mock(return_value=httpx.Response(200, json={"result": {"SuspendResults": [{"Id": 101}]}}))
    res = await _server().call_tool("pause_resume", {"campaign_id": "101", "action": "pause"})
    assert json.loads(route.calls[0].request.content) == {"method": "suspend", "params": {"SelectionCriteria": {"Ids": [101]}}}
    assert res.structured_content["suspend_result"] == {"Id": 101}
    await _server().call_tool("pause_resume", {"campaign_id": "101", "action": "resume"})
    assert json.loads(route.calls[1].request.content)["method"] == "resume"


@pytest.mark.asyncio
@respx.mock
async def test_error_object_in_a_200_body_is_a_failure():
    respx.post(f"{A}/clients").mock(return_value=httpx.Response(200, json={"error": {"request_id": "1", "error_code": 53, "error_string": "Authorization error", "error_detail": "Invalid OAuth token y0_yandextoken"}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and "y0_yandextoken" not in json.dumps(res.structured_content)
