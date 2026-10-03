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

SPEC = json.loads((ROOT / "catalog" / "ads" / "cj_affiliate.json").read_text(encoding="utf-8"))
Q = "https://commissions.api.cj.com/query"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"personal_access_token": "cj-pat-secret", "company_id": "11223344"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {"me", "get_report"}


@pytest.mark.asyncio
@respx.mock
async def test_get_report_sends_graphql_variables_and_maps_records():
    route = respx.post(Q).mock(return_value=httpx.Response(200, json={"data": {"advertiserCommissions": {"count": 1, "payloadComplete": True, "records": [
        {"commissionId": "2292067663", "orderId": "A1", "postingDate": "2026-09-02T10:00:00Z", "actionStatus": "new", "publisherId": "999", "publisherName": "Blog",
         "original": True, "saleAmountAdvCurrency": "75.47", "advCommissionAmountAdvCurrency": "7.55", "cjFeeAdvCurrency": "2.26"}]}}}))
    res = await _server().call_tool("get_report", {"account_id": "11223344", "date_from": "2026-09-01", "date_to": "2026-09-08"})
    assert res.is_error is False
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Bearer cj-pat-secret"
    body = json.loads(req.content)
    assert body["variables"] == {"advertisers": ["11223344"], "since": "2026-09-01T00:00:00Z", "before": "2026-09-08T00:00:00Z"}
    assert body["query"].startswith("query($advertisers: [String!]!")
    r = res.structured_content["rows"][0]
    assert (r["commission_id"], r["spend"], r["cj_fee"], res.structured_content["total"]) == ("2292067663", "7.55", "2.26", 1)


@pytest.mark.asyncio
@respx.mock
async def test_me_uses_configured_cid():
    route = respx.post(Q).mock(return_value=httpx.Response(200, json={"data": {"advertiserCommissions": {"count": 0, "payloadComplete": True}}}))
    res = await _server().call_tool("me", {})
    assert res.is_error is False and res.structured_content["ok"] is True
    assert json.loads(route.calls[0].request.content)["variables"] == {"advertisers": ["11223344"]}


@pytest.mark.asyncio
@respx.mock
async def test_unauthorized_does_not_leak_token():
    respx.post(Q).mock(return_value=httpx.Response(401, json={"data": None, "errors": [{"message": "Unauthorized cj-pat-secret"}]}))
    res = await _server().call_tool("get_report", {"account_id": "1", "date_from": "2026-09-01", "date_to": "2026-09-02"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "cj-pat-secret" not in json.dumps(res.structured_content)
