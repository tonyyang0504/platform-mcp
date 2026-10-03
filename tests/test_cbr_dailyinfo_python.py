"""Bank of Russia DailyInfo (forge stress test 2026-10, SOAP/WSDL, Russian docs): SOAP envelopes built from dotted
XML body keys, a SOAPAction header, .NET DataSet answers (diffgram rows), path "" (the service URL itself)."""
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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "cbr_dailyinfo.json").read_text(encoding="utf-8"))
URL = "https://www.cbr.ru/DailyInfoWebServ/DailyInfo.asmx"
DYN = ('<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
       '<GetCursDynamicResponse xmlns="http://web.cbr.ru/"><GetCursDynamicResult><xs:schema id="ValuteData" xmlns="" xmlns:xs="http://www.w3.org/2001/XMLSchema"/>'
       '<diffgr:diffgram xmlns:msdata="urn:schemas-microsoft-com:xml-msdata" xmlns:diffgr="urn:schemas-microsoft-com:xml-diffgram-v1"><ValuteData xmlns="">'
       '<ValuteCursDynamic diffgr:id="ValuteCursDynamic1" msdata:rowOrder="0"><CursDate>2026-09-25T00:00:00+03:00</CursDate><Vcode>R01235</Vcode><Vnom>1</Vnom><Vcurs>84.9057</Vcurs><VunitRate>84.9057</VunitRate></ValuteCursDynamic>'
       '<ValuteCursDynamic diffgr:id="ValuteCursDynamic2" msdata:rowOrder="1"><CursDate>2026-09-26T00:00:00+03:00</CursDate><Vcode>R01235</Vcode><Vnom>1</Vnom><Vcurs>84.3414</Vcurs><VunitRate>84.3414</VunitRate></ValuteCursDynamic>'
       '</ValuteData></diffgr:diffgram></GetCursDynamicResult></GetCursDynamicResponse></soap:Body></soap:Envelope>')
ENUM = ('<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><EnumValutesResponse xmlns="http://web.cbr.ru/">'
        '<EnumValutesResult><diffgr:diffgram xmlns:diffgr="urn:schemas-microsoft-com:xml-diffgram-v1"><ValuteData xmlns="">'
        '<EnumValutes><Vcode>R01235</Vcode><Vname>Доллар США</Vname><VEngname>US Dollar</VEngname><VcharCode>USD</VcharCode></EnumValutes>'
        '<EnumValutes><Vcode>R01239</Vcode><Vname>Евро</Vname><VEngname>Euro</VEngname><VcharCode>EUR</VcharCode></EnumValutes>'
        '</ValuteData></diffgr:diffgram></EnumValutesResult></EnumValutesResponse></soap:Body></soap:Envelope>')


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_soap_envelope_and_dataset_rows():
    route = respx.post(URL).mock(return_value=httpx.Response(200, headers={"content-type": "text/xml; charset=utf-8"}, text=DYN))
    pts = (await _server().call_tool("get_series", {"series_id": "R01235", "start": "2026-09-25", "end": "2026-09-30"})).structured_content["points"]
    assert [(p["time"], p["value"]) for p in pts] == [("2026-09-25T00:00:00+03:00", 84.9057), ("2026-09-26T00:00:00+03:00", 84.3414)]
    req = route.calls.last.request
    assert req.headers["SOAPAction"] == '"http://web.cbr.ru/GetCursDynamic"' and req.headers["content-type"].startswith("text/xml")
    body = req.content.decode()
    assert '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><GetCursDynamic xmlns="http://web.cbr.ru/">' in body
    assert "<FromDate>2026-09-25</FromDate><ToDate>2026-09-30</ToDate><ValutaCode>R01235</ValutaCode>" in body


@pytest.mark.asyncio
@respx.mock
async def test_currency_list_russian_names_and_fault():
    respx.post(URL).mock(return_value=httpx.Response(200, headers={"content-type": "text/xml"}, text=ENUM))
    r = (await _server().call_tool("search_symbols", {"query": "евро"})).structured_content
    assert [x["symbol"] for x in r["results"]] == ["R01239"] and r["results"][0]["name"] == "Euro"
    respx.post(URL).mock(return_value=httpx.Response(500, headers={"content-type": "text/xml"}, text="<soap:Envelope xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\"><soap:Body><soap:Fault><faultstring>Server was unable to read request.</faultstring></soap:Fault></soap:Body></soap:Envelope>"))
    bad = await _server().call_tool("get_series", {"series_id": "R01235", "start": "x"})
    assert bad.is_error and bad.structured_content["error"] == "invalid_input"
