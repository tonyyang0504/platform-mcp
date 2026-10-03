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

SPEC = json.loads((ROOT / "catalog" / "sales" / "us_sec_edgar.json").read_text(encoding="utf-8"))

SUBMISSIONS = {"cik": "0000320193", "entityType": "operating", "sic": "3571", "sicDescription": "Electronic Computers", "name": "Apple Inc.",
               "tickers": ["AAPL"], "exchanges": ["Nasdaq"], "website": "", "stateOfIncorporation": "CA",
               "addresses": {"business": {"street1": "ONE APPLE PARK WAY", "city": "CUPERTINO", "stateOrCountry": "CA", "zipCode": "95014"}},
               "formerNames": [], "filings": {"recent": {}}}


def _server(monkeypatch=None):
    if monkeypatch is not None:  # exercise the real credential path: config field -> User-Agent
        monkeypatch.setenv("PLATFORM_MCP_US_SEC_EDGAR_CONTACT", "Sample Company Name AdminContact@sample.example")
        return build_server(SPEC)
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"contact": "x"}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_sales_vocabulary():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["get_company"]  # me / search are not offered
    get = tools[0]
    assert get.annotations.read_only_hint is True and get.input_schema["required"] == ["id"]
    assert get.meta["platform_mcp/endpoint"] == "/submissions/CIK{id}.json"
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "search"}
    assert SPEC["adapter"]["user_agent_field"] == "contact"


@pytest.mark.asyncio
@respx.mock
async def test_get_company_uses_the_padded_cik_and_the_contact_user_agent(monkeypatch):
    route = respx.get("https://data.sec.gov/submissions/CIK0000320193.json").mock(return_value=httpx.Response(200, json=SUBMISSIONS))
    res = await _server(monkeypatch).call_tool("get_company", {"id": "0000320193"})
    assert res.is_error is False
    sc = res.structured_content
    assert sc["id"] == "0000320193" and sc["name"] == "Apple Inc." and sc["industry"] == "Electronic Computers" and sc["address"] == "ONE APPLE PARK WAY"
    assert sc["raw"]["tickers"] == ["AAPL"]
    ua = route.calls.last.request.headers["User-Agent"]
    assert ua.startswith("platform-mcp/us_sec_edgar") and ua.endswith("Sample Company Name AdminContact@sample.example")
    assert "Authorization" not in route.calls.last.request.headers


@pytest.mark.asyncio
async def test_missing_contact_is_an_auth_error_result(monkeypatch):
    monkeypatch.delenv("PLATFORM_MCP_US_SEC_EDGAR_CONTACT", raising=False)
    res = await build_server(SPEC).call_tool("get_company", {"id": "0000320193"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "PLATFORM_MCP_US_SEC_EDGAR_CONTACT" in res.structured_content["message"]


@pytest.mark.asyncio
@respx.mock
async def test_blocked_request_is_an_error_result():
    respx.get("https://data.sec.gov/submissions/CIK0000320193.json").mock(return_value=httpx.Response(403, text="Request Rate Threshold Exceeded"))
    res = await _server().call_tool("get_company", {"id": "0000320193"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error" and res.structured_content["http_status"] == 403
