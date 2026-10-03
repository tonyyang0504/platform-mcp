import hashlib
import hmac
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

SPEC = json.loads((ROOT / "catalog" / "deals" / "aws_partner_network.json").read_text(encoding="utf-8"))
URL = "https://partnercentral-selling.us-east-1.api.aws/"
CREDS = {"access_key_id": "AKIDEXAMPLE", "secret_access_key": "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"}


def _server(creds=None):
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], dict(creds or CREDS), 50, "test")
    t.fixed_headers = a.get("headers")
    return build_server(SPEC, transport=t)


def _expected_auth(req, amz_date, token=None):
    date = amz_date[:8]
    signed = {"host": "partnercentral-selling.us-east-1.api.aws", "x-amz-date": amz_date}
    if token:
        signed["x-amz-security-token"] = token
    names = sorted(signed)
    canonical = "\n".join(["POST", "/", "", "".join(f"{n}:{signed[n]}\n" for n in names), ";".join(names), hashlib.sha256(req.content).hexdigest()])
    scope = f"{date}/us-east-1/partnercentral-selling/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    k = ("AWS4" + CREDS["secret_access_key"]).encode()
    for part in (date, "us-east-1", "partnercentral-selling", "aws4_request"):
        k = hmac.new(k, part.encode(), hashlib.sha256).digest()
    sig = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    return f"AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/{scope}, SignedHeaders={';'.join(names)}, Signature={sig}"


@pytest.mark.asyncio
@respx.mock
async def test_list_invitations_is_sigv4_signed_json10(monkeypatch):
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1790301600.0)
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"NextToken": "tok-2", "EngagementInvitationSummaries": [
        {"Id": "engi-0123456789abc", "EngagementTitle": "Data lake migration", "SenderCompanyName": "AWS", "InvitationDate": "2026-09-20T10:00:00Z",
         "ExpirationDate": "2026-10-05T10:00:00Z", "Status": "PENDING"}]}))
    res = await _server().call_tool("search_postings", {"limit": 10})
    p = res.structured_content["postings"][0]
    assert p["id"] == "engi-0123456789abc" and p["title"] == "Data lake migration" and p["deadline"] == "2026-10-05T10:00:00Z"
    assert res.structured_content["next_cursor"] == "tok-2"
    req = route.calls.last.request
    assert json.loads(req.content) == {"Catalog": "AWS", "ParticipantType": "RECEIVER", "MaxResults": 10}
    assert req.headers["X-Amz-Target"] == "AWSPartnerCentralSelling.ListEngagementInvitations"
    assert req.headers["Content-Type"] == "application/x-amz-json-1.0"
    assert req.headers["X-Amz-Date"] == "20260925T020000Z"
    assert req.headers["Authorization"] == _expected_auth(req, "20260925T020000Z")


@pytest.mark.asyncio
@respx.mock
async def test_accept_invitation_and_poll_task(monkeypatch):
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1790301600.0)
    route = respx.post(URL).mock(side_effect=[
        httpx.Response(200, json={"TaskId": "task-0123456789abc", "TaskStatus": "IN_PROGRESS", "EngagementInvitationId": "engi-0123456789abc"}),
        httpx.Response(200, json={"TaskSummaries": [{"TaskId": "task-0123456789abc", "TaskStatus": "COMPLETE", "OpportunityId": "O1234567"}]}),
    ])
    creds = {**CREDS, "session_token": "SESSION-TOKEN-aws"}
    server = _server(creds)
    out = (await server.call_tool("submit_bid", {"posting_id": "engi-0123456789abc", "amount": 0})).structured_content
    assert out["bid_id"] == "task-0123456789abc" and out["status"] == "IN_PROGRESS"
    first = route.calls[0].request
    body = json.loads(first.content)
    assert body["Catalog"] == "AWS" and body["Identifier"] == "engi-0123456789abc" and len(body["ClientToken"]) == 36
    assert first.headers["X-Amz-Target"] == "AWSPartnerCentralSelling.StartEngagementByAcceptingInvitationTask"
    assert first.headers["X-Amz-Security-Token"] == "SESSION-TOKEN-aws"
    assert first.headers["Authorization"] == _expected_auth(first, "20260925T020000Z", "SESSION-TOKEN-aws")
    st = (await server.call_tool("bid_status", {"bid_id": "task-0123456789abc"})).structured_content
    assert st["status"] == "COMPLETE" and st["raw"]["OpportunityId"] == "O1234567"
    assert json.loads(route.calls[1].request.content) == {"Catalog": "AWS", "TaskIdentifier": ["task-0123456789abc"]}


@pytest.mark.asyncio
@respx.mock
async def test_access_denied_is_upstream_error_and_get_posting():
    respx.post(URL).mock(side_effect=[
        httpx.Response(200, json={"Id": "engi-0123456789abc", "EngagementTitle": "T", "EngagementDescription": "D", "Status": "PENDING"}),
        httpx.Response(400, json={"__type": "AccessDeniedException", "message": "You don't have access"}),
    ])
    server = _server()
    g = (await server.call_tool("get_posting", {"id": "engi-0123456789abc"})).structured_content
    assert g["title"] == "T" and g["description"] == "D"
    assert (await server.call_tool("me", {})).is_error is True
