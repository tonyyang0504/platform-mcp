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

SPEC = json.loads((ROOT / "catalog" / "ads" / "qihoo_360_ads.json").read_text(encoding="utf-8"))
B = "https://api.e.360.cn"
ENC = "9f" * 32


def _server():
    creds = {"api_key": "APIKEY-360", "username": "dj-user", "encrypted_password": ENC}
    return build_server(SPEC, transport=Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], creds, 50, "test", envelope=SPEC["adapter"]["envelope"]))


def _login():
    return respx.post(f"{B}/uc/account/clientLogin").mock(return_value=httpx.Response(200, json={"uid": "2563420133", "accessToken": "ACCESS-360"}))


def _form(req):
    return {k: v[0] for k, v in parse_qs(req.content.decode()).items()}


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "get_report", "update_budget", "pause_resume"}


@pytest.mark.asyncio
@respx.mock
async def test_client_login_with_apikey_header_then_token_headers():
    login = _login()
    me = respx.post(f"{B}/uc/account/getInfo").mock(return_value=httpx.Response(200, json={"uid": "160185657", "userName": "点睛广告测试", "balance": 31514.28}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["account"]["userName"] == "点睛广告测试"
    req = login.calls[0].request
    assert req.headers["apiKey"] == "APIKEY-360" and _form(req) == {"username": "dj-user", "passwd": ENC}
    call = me.calls[0].request
    assert call.headers["apiKey"] == "APIKEY-360" and call.headers["accessToken"] == "ACCESS-360" and "Authorization" not in call.headers


@pytest.mark.asyncio
@respx.mock
async def test_campaign_report_form_and_rows():
    _login()
    route = respx.post(f"{B}/dianjing/report/campaign").mock(return_value=httpx.Response(200, json={"campaignList": [
        {"campaignId": 4024958540, "campaignName": "推广计划名称", "date": "2026-09-01", "views": "2000", "clicks": "100", "totalCost": "10.00"}]}))
    res = await _server().call_tool("get_report", {"account_id": "x", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert res.is_error is False
    row = res.structured_content["rows"][0]
    assert (row["campaign_id"], row["impressions"], row["spend"]) == ("4024958540", "2000", "10.00")
    assert _form(route.calls[0].request) == {"startDate": "2026-09-01", "endDate": "2026-09-07", "type": "all", "page": "1"}


@pytest.mark.asyncio
@respx.mock
async def test_campaign_update_forms_and_failures_envelope():
    _login()
    route = respx.post(f"{B}/dianjing/campaign/update").mock(side_effect=[
        httpx.Response(200, json={"id": "3907501127"}),
        httpx.Response(200, json={"id": "3907501127"}),
        httpx.Response(200, json={"affectedRecords": [], "failures": [{"id": 3907501127, "code": 30503, "message": "推广计划每日预算格式不正确", "description": "_param.budget"}]})])
    s = _server()
    res = await s.call_tool("update_budget", {"campaign_id": "3907501127", "daily_budget": 230})
    assert res.is_error is False and res.structured_content["campaign_id"] == "3907501127"
    assert _form(route.calls[0].request) == {"id": "3907501127", "budget": "230"}
    await s.call_tool("pause_resume", {"campaign_id": "3907501127", "action": "resume"})
    assert _form(route.calls[1].request) == {"id": "3907501127", "status": "enable"}
    bad = await s.call_tool("update_budget", {"campaign_id": "3907501127", "daily_budget": 10})
    assert bad.is_error is True
