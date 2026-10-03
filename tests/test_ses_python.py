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

SPEC = json.loads((ROOT / "catalog" / "messaging" / "ses.json").read_text(encoding="utf-8"))
CREDS = {"access_key_id": "AKIDSESEXAMPLE", "secret_access_key": "sesSecretKey/EXAMPLE+0123456789", "region": "eu-west-1", "from_address": "shop@example.com"}
HOST = "email.eu-west-1.amazonaws.com"


def _server(creds=None):
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(creds or CREDS), 50, "test"))


def _expected_auth(method, path, body, amz_date, extra=None):
    signed = {"host": HOST, "x-amz-date": amz_date, **(extra or {})}
    names = sorted(signed)
    canonical = "\n".join([method, path, "", "".join(f"{n}:{signed[n]}\n" for n in names), ";".join(names), hashlib.sha256(body).hexdigest()])
    scope = f"{amz_date[:8]}/eu-west-1/ses/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    k = ("AWS4" + CREDS["secret_access_key"]).encode()
    for part in (amz_date[:8], "eu-west-1", "ses", "aws4_request"):
        k = hmac.new(k, part.encode(), hashlib.sha256).digest()
    sig = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    return f"AWS4-HMAC-SHA256 Credential={CREDS['access_key_id']}/{scope}, SignedHeaders={';'.join(names)}, Signature={sig}"


@pytest.mark.asyncio
@respx.mock
async def test_send_email_is_sigv4_signed_over_the_body(monkeypatch):
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1790301600.0)
    route = respx.post(f"https://{HOST}/v2/email/outbound-emails").mock(return_value=httpx.Response(200, json={"MessageId": "0102018f-abc"}))
    res = await _server().call_tool("send", {"to": "ann@example.org", "text": "Your order shipped", "subject": "Order 42"})
    assert res.is_error is False and res.structured_content["message_id"] == "0102018f-abc"
    req = route.calls[0].request
    assert json.loads(req.content) == {"FromEmailAddress": "shop@example.com", "Destination": {"ToAddresses": ["ann@example.org"]},
                                       "Content": {"Simple": {"Subject": {"Data": "Order 42", "Charset": "UTF-8"}, "Body": {"Text": {"Data": "Your order shipped", "Charset": "UTF-8"}}}}}
    assert req.headers["X-Amz-Date"] == "20260925T020000Z"
    assert req.headers["Authorization"] == _expected_auth("POST", "/v2/email/outbound-emails", req.content, "20260925T020000Z")


@pytest.mark.asyncio
@respx.mock
async def test_get_account_with_session_token(monkeypatch):
    import time as _t
    monkeypatch.setattr(_t, "time", lambda: 1790301600.0)
    route = respx.get(f"https://{HOST}/v2/email/account").mock(return_value=httpx.Response(200, json={"SendingEnabled": True, "ProductionAccessEnabled": False, "SendQuota": {"Max24HourSend": 200}}))
    res = await _server({**CREDS, "session_token": "STS-TOKEN-1"}).call_tool("me", {})
    assert res.structured_content["account"]["SendQuota"]["Max24HourSend"] == 200
    h = route.calls[0].request.headers
    assert h["X-Amz-Security-Token"] == "STS-TOKEN-1"
    assert h["Authorization"] == _expected_auth("GET", "/v2/email/account", b"", "20260925T020000Z", {"x-amz-security-token": "STS-TOKEN-1"})


@pytest.mark.asyncio
@respx.mock
async def test_signature_mismatch_is_an_auth_error_without_the_secret():
    respx.get(f"https://{HOST}/v2/email/account").mock(return_value=httpx.Response(403, json={"message": "The request signature we calculated does not match the signature you provided."}))
    res = await _server().call_tool("me", {})
    assert res.is_error is True and res.structured_content["error"] == "auth_error"
    assert CREDS["secret_access_key"] not in json.dumps(res.structured_content)
