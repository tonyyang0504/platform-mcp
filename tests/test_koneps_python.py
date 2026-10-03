import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub.http import Transport  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

SPEC = json.loads((ROOT / "catalog" / "deals" / "koneps.json").read_text(encoding="utf-8"))
BASE = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"
ITEM = ("<item><bidNtceNo>R25BK00933736</bidNtceNo><bidNtceOrd>000</bidNtceOrd><bidNtceDt>2025-07-01 09:28:14</bidNtceDt>"
        "<bidNtceNm>AI 기반 탄소 데이터 정제 알고리즘 개발 용역</bidNtceNm><ntceInsttNm>한국생산기술연구원</ntceInsttNm><dminsttNm>한국생산기술연구원</dminsttNm>"
        "<bidClseDt>2025-07-15 10:00:00</bidClseDt><presmptPrce>46363636</presmptPrce>"
        "<bidNtceDtlUrl>https://www.g2b.go.kr/link/PNPE027_01/single/?bidPbancNo=R25BK00933736&amp;bidPbancOrd=000</bidNtceDtlUrl></item>")
XML = f"<response><header><resultCode>00</resultCode><resultMsg>정상</resultMsg></header><body><items>{ITEM}{ITEM.replace('R25BK00933736', 'R25BK00933737')}</items><numOfRows>10</numOfRows><pageNo>2</pageNo><totalCount>2</totalCount></body></response>"


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {"service_key": "KEY-abc123=="}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_search_and_get_are_offered_read_only():
    tools = await _server().list_tools()
    assert sorted(t.name for t in tools) == ["get_posting", "search_postings"]
    assert all(t.annotations.read_only_hint for t in tools)


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_compact_date_window_and_maps_xml_items():
    route = respx.get(url__startswith=BASE + "/getBidPblancListInfoServcPPSSrch").mock(return_value=httpx.Response(200, headers={"content-type": "application/xml"}, text=XML))
    res = await _server().call_tool("search_postings", {"query": "AI", "min_budget": 5000000, "page": 2, "limit": 10})
    assert res.is_error is False, res.structured_content
    p = res.structured_content["postings"]
    assert [x["id"] for x in p] == ["R25BK00933736", "R25BK00933737"]
    assert p[0]["title"] == "AI 기반 탄소 데이터 정제 알고리즘 개발 용역" and p[0]["buyer"] == "한국생산기술연구원"
    assert p[0]["url"] == "https://www.g2b.go.kr/link/PNPE027_01/single/?bidPbancNo=R25BK00933736&bidPbancOrd=000"
    assert p[0]["posted_at"] == "2025-07-01 09:28:14" and p[0]["deadline"] == "2025-07-15 10:00:00" and p[0]["currency"] == "KRW"
    assert p[0]["raw"]["presmptPrce"] == "46363636" and "budget_max" not in p[0]
    q = route.calls.last.request.url.params
    assert q["serviceKey"] == "KEY-abc123==" and q["pageNo"] == "2" and q["numOfRows"] == "10" and q["inqryDiv"] == "1"
    assert q["bidNtceNm"] == "AI" and q["presmptPrceBgn"] == "5000000" and q["bidClseExcpYn"] == "Y"
    assert re.fullmatch(r"\d{12}", q["inqryBgnDt"]) and re.fullmatch(r"\d{12}", q["inqryEndDt"])
    assert q["inqryBgnDt"].endswith("0000") and q["inqryBgnDt"][:8] == (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y%m%d")
    assert q["inqryEndDt"][:8] == datetime.now(timezone.utc).strftime("%Y%m%d")
    assert "type" not in q  # XML (the documented default) is parsed natively


@pytest.mark.asyncio
@respx.mock
async def test_get_posting_looks_up_by_notice_number():
    route = respx.get(url__startswith=BASE + "/getBidPblancListInfoServc?").mock(return_value=httpx.Response(200, headers={"content-type": "application/xml"},
        text=f"<response><header><resultCode>00</resultCode></header><body><items>{ITEM}</items><totalCount>1</totalCount></body></response>"))
    res = await _server().call_tool("get_posting", {"id": "R25BK00933736"})
    assert res.is_error is False and res.structured_content["id"] == "R25BK00933736" and res.structured_content["deadline"] == "2025-07-15 10:00:00"
    q = route.calls.last.request.url.params
    assert q["inqryDiv"] == "2" and q["bidNtceNo"] == "R25BK00933736" and q["numOfRows"] == "1" and q["serviceKey"] == "KEY-abc123=="


@pytest.mark.asyncio
@respx.mock
async def test_unknown_notice_and_rate_limit():
    respx.get(url__startswith=BASE + "/getBidPblancListInfoServc?").mock(return_value=httpx.Response(200, headers={"content-type": "application/xml"},
        text="<response><header><resultCode>00</resultCode></header><body><items/><totalCount>0</totalCount></body></response>"))
    res = await _server().call_tool("get_posting", {"id": "NOPE"})
    assert res.is_error is True and res.structured_content["error"] == "not_found"
    respx.get(url__startswith=BASE + "/getBidPblancListInfoServcPPSSrch").mock(return_value=httpx.Response(429, headers={"Retry-After": "5"}))
    res = await _server().call_tool("search_postings", {})
    assert res.is_error is True and res.structured_content["error"] == "rate_limited"
    assert "KEY-abc123" not in json.dumps(res.structured_content)
