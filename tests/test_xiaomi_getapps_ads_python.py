import json
import re
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "ads" / "xiaomi_getapps_ads.json").read_text(encoding="utf-8"))
BASE = "https://global.e.mi.com"
CREDS = {"app_id": "wmsj", "app_key": "APPKEY-mi-secret"}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _login():
    return respx.post(f"{BASE}/foreign/token/createToken").mock(return_value=httpx.Response(200, json={
        "code": 0, "message": "成功", "result": {"accessToken": "ACCESS-mi", "expireDate": "2026-09-25T10:28:04.570Z", "refreshToken": "R", "refreshExpireDate": "2026-10-02T09:28:04.570Z"}}))


@pytest.mark.asyncio
@respx.mock
async def test_token_login_and_cookie_parameters():
    login = _login()
    route = respx.get(url__startswith=f"{BASE}/foreign/marketing/campaign/list").mock(return_value=httpx.Response(200, json={
        "code": 0, "message": "成功", "result": {"size": 10, "total": 2, "current": 1, "pages": 1, "records": [
            {"accountId": 1, "campaignId": 100205030, "name": "计划1", "dayBudget": 3000000, "campaignType": 1}]}}))
    server = _server()
    res = await server.call_tool("list_campaigns", {"account_id": "1420", "limit": 10})
    c = res.structured_content["campaigns"][0]
    assert c["id"] == "100205030" and c["name"] == "计划1" and res.structured_content["total"] == 2
    assert json.loads(login.calls[0].request.content) == {"appId": "wmsj", "appKey": "APPKEY-mi-secret"}
    req = route.calls[0].request
    assert re.fullmatch(r"access_token=ACCESS-mi; timestamp=\d{13}; uid=[0-9a-f]{32}", req.headers["Cookie"])
    assert "Authorization" not in req.headers
    assert req.url.params["accountIds"] == "1420" and req.url.params["pageSize"] == "10"
    await server.call_tool("list_campaigns", {"account_id": "1420"})
    uids = {r.request.headers["Cookie"].split("uid=")[1] for r in route.calls}
    assert len(uids) == 2 and len(login.calls) == 1


@pytest.mark.asyncio
@respx.mock
async def test_group_budget_in_dollar_units_and_error_code():
    _login()
    up = respx.post(f"{BASE}/foreign/marketing/group/update").mock(return_value=httpx.Response(200, json={"code": 0, "message": "成功"}))
    server = _server()
    assert (await server.call_tool("update_budget", {"campaign_id": "32434", "daily_budget": 5})).structured_content["status"] == "updated"
    assert json.loads(up.calls[0].request.content) == {"groupIds": [32434], "dayBudget": 500000}
    respx.post(f"{BASE}/foreign/marketing/group/update").mock(return_value=httpx.Response(200, json={"code": 10004, "message": "accountId未授权"}))
    assert (await server.call_tool("update_budget", {"campaign_id": "32434", "daily_budget": 5})).is_error is True


@pytest.mark.asyncio
@respx.mock
async def test_probe_and_tool_list():
    _login()
    # auth audit: campaign/list without accountIds is refused before authentication (code 100500), so the probe is countryList
    r = respx.get(f"{BASE}/foreign/marketing/region/countryList").mock(return_value=httpx.Response(200, json={"code": 0, "message": "成功", "result": [{"geoType": "COUNTRY", "id": "AF", "name": "Afghanistan"}]}))
    server = _server()
    assert (await server.call_tool("me", {})).is_error is False
    assert r.called and not r.calls[0].request.url.params
    assert sorted(t.name for t in await server.list_tools()) == ["list_campaigns", "me", "update_budget"]
