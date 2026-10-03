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

SPEC = json.loads((ROOT / "catalog" / "deals" / "upwork.json").read_text(encoding="utf-8"))
GQL = "https://api.upwork.com/graphql"
TOKEN_URL = "https://www.upwork.com/api/v3/oauth2/token"
CREDS = {"client_id": "upw-cid", "client_secret": "upw-secret-123456", "refresh_token": "oauth2v2_refresh_abcdef", "tenant_id": "470123"}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a["envelope"])
    return build_server(SPEC, transport=t)


def _token():
    return respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "oauth2v2_access_1", "refresh_token": "oauth2v2_refresh_new", "token_type": "Bearer", "expires_in": 86400}))


@pytest.mark.asyncio
async def test_tool_list():
    names = sorted(t.name for t in await _server().list_tools())
    assert names == ["bid_status", "get_posting", "list_messages", "me", "search_postings", "send_message"]
    assert set(SPEC["adapter"]["not_offered"]) == {"submit_bid", "withdraw_bid", "credits"}


@pytest.mark.asyncio
@respx.mock
async def test_search_posts_documented_query_with_filter_variables():
    tok = _token()
    route = respx.post(GQL).mock(return_value=httpx.Response(200, json={"data": {"marketplaceJobPostingsSearch": {"totalCount": 987, "edges": [
        {"node": {"id": "2056488576136638272", "title": "PHP developer", "description": "Fix a Laravel app", "ciphertext": "~01abc",
                  "publishedDateTime": "2026-09-24T10:00:00.000Z", "amount": {"rawValue": "500.0", "currency": "USD", "displayValue": "$500.00"},
                  "skills": [{"name": "PHP"}]}}], "pageInfo": {"endCursor": "20", "hasNextPage": True}}}}))
    res = await _server().call_tool("search_postings", {"query": "php", "category": "531770282580668418", "min_budget": 300, "page": 3, "limit": 10})
    assert res.is_error is False
    form = {k: v[0] for k, v in parse_qs(tok.calls.last.request.content.decode()).items()}
    assert form["grant_type"] == "refresh_token" and form["refresh_token"] == "oauth2v2_refresh_abcdef" and form["client_id"] == "upw-cid"
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer oauth2v2_access_1" and req.headers["X-Upwork-API-TenantId"] == "470123"
    body = json.loads(req.content)
    assert "marketplaceJobPostingsSearch(marketPlaceJobFilter: $filter" in body["query"] and "USER_JOBS_SEARCH" in body["query"]
    assert body["variables"] == {"filter": {"searchExpression_eq": "php", "categoryIds_any": ["531770282580668418"],
                                            "budgetRange_eq": {"rangeStart": 300}, "pagination_eq": {"after": "20", "first": 10}}}
    sc = res.structured_content
    p = sc["postings"][0]
    assert p["id"] == "2056488576136638272" and p["title"] == "PHP developer" and p["currency"] == "USD" and p["raw"]["node"]["amount"]["rawValue"] == "500.0"
    assert sc["total"] == 987


@pytest.mark.asyncio
@respx.mock
async def test_send_message_variables_and_result():
    _token()
    route = respx.post(GQL).mock(return_value=httpx.Response(200, json={"data": {"createRoomStoryV2": {"id": "story_1", "message": "Hello"}}}))
    res = await _server().call_tool("send_message", {"thread_id": "room_d4ad627e8343569efaa2ee76260170a3", "text": "Hello"})
    assert res.is_error is False and res.structured_content["message_id"] == "story_1" and res.structured_content["status"] == "sent"
    body = json.loads(route.calls.last.request.content)
    assert body["variables"] == {"roomId": "room_d4ad627e8343569efaa2ee76260170a3", "message": "Hello"} and body["query"].startswith("mutation SendRoomMessage")


@pytest.mark.asyncio
@respx.mock
async def test_graphql_error_with_null_data_is_an_error_and_scrubs_secrets():
    _token()
    respx.post(GQL).mock(return_value=httpx.Response(200, json={"data": None, "errors": [{"message": "Authorization failed for oauth2v2_access_1 (upw-secret-123456)"}]}))
    res = await _server().call_tool("bid_status", {"bid_id": "1"})
    assert res.is_error is True
    dumped = json.dumps(res.structured_content)
    assert "upw-secret-123456" not in dumped and "oauth2v2_access_1" not in dumped


@pytest.mark.asyncio
@respx.mock
async def test_bid_status_maps_vendor_proposal_status():
    _token()
    respx.post(GQL).mock(return_value=httpx.Response(200, json={"data": {"vendorProposal": {"id": "1600000000000000001", "status": {"status": "Offered"}, "viewedByClient": True}}}))
    res = await _server().call_tool("bid_status", {"bid_id": "1600000000000000001"})
    assert res.is_error is False and res.structured_content == {"bid_id": "1600000000000000001", "status": "Offered", "raw": {"id": "1600000000000000001", "status": {"status": "Offered"}, "viewedByClient": True}}
