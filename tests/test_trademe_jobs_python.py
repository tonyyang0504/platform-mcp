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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "trademe_jobs.json").read_text(encoding="utf-8"))
BASE = "https://api.trademe.co.nz/v1"
CREDS = {"consumer_key": "CK4E0D0823", "consumer_secret": "CSEC160FCF", "oauth_token": "TOKFC68E514", "oauth_token_secret": "TSEC5333F6"}
JOB = {"ListingId": 4912345678, "Title": "Senior Developer", "Company": "Kiwi Ltd", "Region": "Wellington", "District": "Wellington City",
       "StartDate": "/Date(1790000000000)/", "JobType": "FT", "PayBenefits": "$120k + KiwiSaver"}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], dict(CREDS), 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_tools_follow_the_vocabulary():
    assert sorted(t.name for t in await _server().list_tools()) == ["get_posting", "me", "search"]


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_the_oauth_plaintext_header_and_maps_jobs():
    route = respx.get(BASE + "/Search/Jobs.json").mock(return_value=httpx.Response(200, json={"TotalCount": 120, "Page": 2, "PageSize": 25, "List": [JOB]}))
    res = await _server().call_tool("search", {"query": "developer", "page": 2, "limit": 25, "location": "Wellington"})
    assert res.is_error is False, res.structured_content
    p = res.structured_content["postings"][0]
    assert p["id"] == "4912345678" and p["company"] == "Kiwi Ltd" and p["location"] == "Wellington" and p["description"] == "$120k + KiwiSaver"
    assert res.structured_content["total"] == 120
    req = route.calls.last.request
    assert dict(req.url.params) == {"search_string": "developer", "page": "2", "rows": "25"}
    assert req.headers["Authorization"] == ("OAuth oauth_consumer_key=CK4E0D0823, oauth_token=TOKFC68E514, "
                                            "oauth_signature_method=PLAINTEXT, oauth_signature=CSEC160FCF%26TSEC5333F6")


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_and_me():
    respx.get(BASE + "/Listings/4912345678.json").mock(return_value=httpx.Response(200, json={**JOB, "Body": "Full description", "Agency": {"Name": "Recruit NZ"}}))
    respx.get(BASE + "/MyTradeMe/Summary.json").mock(return_value=httpx.Response(200, json={"MemberId": 42, "Nickname": "kiwi"}))
    g = await _server().call_tool("get_posting", {"id": "4912345678"})
    assert g.is_error is False and g.structured_content["description"] == "Full description" and g.structured_content["company"] == "Recruit NZ"
    me = await _server().call_tool("me", {})
    assert me.structured_content["ok"] is True and me.structured_content["account"]["Nickname"] == "kiwi"


@pytest.mark.asyncio
@respx.mock
async def test_rejected_credentials_are_an_auth_error_without_leaking_secrets():
    respx.get(BASE + "/Search/Jobs.json").mock(return_value=httpx.Response(401, json={"ErrorDescription": "Invalid signature CSEC160FCF"}))
    res = await _server().call_tool("search", {"query": "x"})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert "CSEC160FCF" not in json.dumps(res.structured_content)
