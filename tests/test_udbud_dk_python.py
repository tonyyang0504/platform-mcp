import json
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import jwt as pyjwt
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "deals" / "udbud_dk.json").read_text(encoding="utf-8"))
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PEM = KEY.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
CREDS = {"client_id": "udbud-client-7", "private_key": PEM, "key_id": "kid-2026"}
TOKEN_URL = "https://auth.virk.dk/realms/erst/protocol/openid-connect/token"
API = "https://api.udbud.dk/udbud/ekstern-data/bekendtgoerelse/v1"
NOTICE = {"noticeId": "6a26cc22-a211-41ea-867f-c34b4d726154", "noticeVersion": "01", "noticePublicationNumber": "00258225-2024",
          "registreringsTidspunkt": "2026-09-20T12:00:00+02:00", "bekendtgoerelseXml": "PENvbnRyYWN0Tm90aWNlLz4="}


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], dict(CREDS), 50, "test", envelope=a.get("envelope")))


def _token():
    return respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "ACCESS-ud-1", "expires_in": 300, "token_type": "Bearer"}))


@pytest.mark.asyncio
@respx.mock
async def test_private_key_jwt_client_assertion():
    tok = _token()
    respx.get(url__startswith=API + "/fraKilde/DKUDBUD").mock(return_value=httpx.Response(200, json={"totalt": 1, "bekendtgoerelser": [NOTICE]}))
    assert (await _server().call_tool("me", {})).is_error is False
    form = {k: v[0] for k, v in parse_qs(tok.calls[0].request.content.decode()).items()}
    assert form["grant_type"] == "client_credentials" and form["client_id"] == "udbud-client-7" and "client_secret" not in form
    assert form["scope"] == "professional dk:gov:virk:roles"
    assert form["client_assertion_type"] == "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
    claims = pyjwt.decode(form["client_assertion"], KEY.public_key(), algorithms=["RS256"], audience=TOKEN_URL)
    assert claims["iss"] == claims["sub"] == "udbud-client-7" and claims["jti"] and 0 < claims["exp"] - claims["iat"] <= 300
    assert pyjwt.get_unverified_header(form["client_assertion"])["kid"] == "kid-2026"


@pytest.mark.asyncio
@respx.mock
async def test_sync_feed_page_and_since():
    _token()
    route = respx.get(url__startswith=API + "/fraKilde/DKUDBUD").mock(return_value=httpx.Response(200, json={"totalt": 153, "bekendtgoerelser": [NOTICE]}))
    res = await _server().call_tool("search_postings", {"page": 2, "limit": 10})
    p = res.structured_content["postings"][0]
    assert p["id"] == NOTICE["noticeId"] and p["version"] == "01" and res.structured_content["total"] == 153
    q = route.calls[0].request.url.params
    assert q["page"] == "2" and q["size"] == "10" and q["since"].endswith("T00:00:00") and len(q["since"]) == 19
    assert route.calls[0].request.headers["Authorization"] == "Bearer ACCESS-ud-1"


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_by_id_and_version_and_missing_role():
    _token()
    respx.get(API + "/6a26cc22-a211-41ea-867f-c34b4d726154/01").mock(return_value=httpx.Response(200, json=NOTICE))
    respx.get(API + "/x/01").mock(return_value=httpx.Response(403, json={"status": "403 FORBIDDEN"}))
    s = _server()
    g = await s.call_tool("get_posting", {"id": "6a26cc22-a211-41ea-867f-c34b4d726154/01"})
    assert g.structured_content["publication_number"] == "00258225-2024" and g.structured_content["xml_base64"] == "PENvbnRyYWN0Tm90aWNlLz4="
    bad = await s.call_tool("get_posting", {"id": "x/01"})
    assert bad.is_error is True and bad.structured_content["error"] == "auth_error"
