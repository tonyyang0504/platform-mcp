import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "builder_tools" / "google_sheets.json").read_text(encoding="utf-8"))
CREDS = {'client_id': 'gcid', 'client_secret': 'gsecret', 'refresh_token': '1//sheets', 'spreadsheet_id': 'SHEET1'}


def _server():
    a = SPEC["adapter"]
    t = Transport(a["base_url"], a["auth"], CREDS, 50, "test", envelope=a.get("envelope"))
    return build_server(SPEC, transport=t)


def _q(req):
    return {k: v[0] for k, v in parse_qs(urlparse(str(req.url)).query).items()}


def _body(req):
    return json.loads(req.content)


@pytest.mark.asyncio
async def test_tool_list():
    assert {t.name for t in await _server().list_tools()} == {'update_item', 'create_item', 'me', 'delete_item', 'list_items', 'get_item'}


B = "https://sheets.googleapis.com/v4/spreadsheets/SHEET1"


def _token():
    return respx.post("https://oauth2.googleapis.com/token").mock(return_value=httpx.Response(200, json={"access_token": "ya29.SH", "expires_in": 3599}))


@pytest.mark.asyncio
@respx.mock
async def test_list_rows_of_range_with_refreshed_token():
    tok = _token()
    route = respx.get(f"{B}/values/Sheet1!A1:C3").mock(return_value=httpx.Response(200, json={"range": "Sheet1!A1:C3", "majorDimension": "ROWS", "values": [["a", "b"], ["1", "2"]]}))
    res = await _server().call_tool("list_items", {"collection": "Sheet1!A1:C3"})
    assert res.is_error is False
    assert parse_qs(tok.calls[0].request.content.decode())["grant_type"] == ["refresh_token"]
    assert route.calls[0].request.headers["Authorization"] == "Bearer ya29.SH"
    assert [i["cells"] for i in res.structured_content["items"]] == [["a", "b"], ["1", "2"]]
    assert res.structured_content["next_page"] is None


@pytest.mark.asyncio
@respx.mock
async def test_append_rows_wire_shape():
    _token()
    route = respx.post(f"{B}/values/Sheet1!A1:append").mock(return_value=httpx.Response(200, json={"spreadsheetId": "SHEET1", "updates": {"updatedRange": "Sheet1!A5:B5", "updatedRows": 1}}))
    res = await _server().call_tool("create_item", {"collection": "Sheet1!A1", "fields": {"values": [["x", 3]]}})
    assert res.is_error is False
    req = route.calls[0].request
    assert _q(req) == {"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"}
    assert _body(req) == {"values": [["x", 3]]}
    assert (res.structured_content["id"], res.structured_content["status"]) == ("Sheet1!A5:B5", "appended")


@pytest.mark.asyncio
@respx.mock
async def test_update_and_clear_range():
    _token()
    up = respx.put(f"{B}/values/Sheet1!B2").mock(return_value=httpx.Response(200, json={"updatedRange": "Sheet1!B2", "updatedCells": 1}))
    cl = respx.post(f"{B}/values/Sheet1!B2:clear").mock(return_value=httpx.Response(200, json={"clearedRange": "Sheet1!B2"}))
    res = await _server().call_tool("update_item", {"item_id": "Sheet1!B2", "fields": {"values": [["9"]]}})
    assert res.structured_content["status"] == "updated" and _body(up.calls[0].request) == {"values": [["9"]]}
    res = await _server().call_tool("delete_item", {"item_id": "Sheet1!B2"})
    assert res.structured_content == {"id": "Sheet1!B2", "status": "cleared", "raw": {"clearedRange": "Sheet1!B2"}} and cl.called


@pytest.mark.asyncio
@respx.mock
async def test_me_reads_configured_spreadsheet():
    _token()
    route = respx.get(B).mock(return_value=httpx.Response(200, json={"spreadsheetId": "SHEET1", "properties": {"title": "Budget"}}))
    res = await _server().call_tool("me", {})
    assert res.structured_content["account"]["properties"]["title"] == "Budget"
    assert _q(route.calls[0].request)["fields"].startswith("spreadsheetId")
