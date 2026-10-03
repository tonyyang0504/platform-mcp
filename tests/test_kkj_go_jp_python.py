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

SPEC = json.loads((ROOT / "catalog" / "deals" / "kkj_go_jp.json").read_text(encoding="utf-8"))
API = "https://www.kkj.go.jp/api/"
XML = ('<?xml version="1.0" encoding="utf-8" ?><Results><Version>1.0</Version><SearchResults><SearchHits>365264</SearchHits>'
       '<SearchResult><ResultId>1</ResultId><Key><![CDATA[ZnVrdXNoaW1hL3RhbXVyYV9jaXR5LzIwMjYK]]></Key>'
       '<ExternalDocumentURI><![CDATA[https://www.city.tamura.lg.jp/soshiki/3/assets/260930.pdf]]></ExternalDocumentURI>'
       '<ProjectName>スタッドレスタイヤ購入</ProjectName><Date>2026-09-04T19:07:48+09:00</Date><FileType>pdf</FileType>'
       '<LgCode>07</LgCode><PrefectureName>福島県</PrefectureName><OrganizationName>福島県田村市</OrganizationName>'
       '<CftIssueDate>2026-09-04T00:00:00+09:00</CftIssueDate><Category>物品</Category>'
       '<TenderSubmissionDeadline>2026-09-29T00:00:00+09:00</TenderSubmissionDeadline><ProjectDescription>田村市公告 第 334 号</ProjectDescription>'
       '<Attachments><Attachment><Name>仕様書</Name><Uri>https://www.city.tamura.lg.jp/a.pdf</Uri></Attachment></Attachments></SearchResult>'
       '<SearchResult><ResultId>2</ResultId><Key>K2</Key><ProjectName>システム保守</ProjectName><CftIssueDate>2026-09-01T00:00:00+09:00</CftIssueDate></SearchResult>'
       '</SearchResults></Results>')


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_search_is_offered():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search_postings"]
    assert tools[0].annotations.read_only_hint is True


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_query_count_and_a_60_day_notice_window_and_parses_xml():
    route = respx.get(url__startswith=API).mock(return_value=httpx.Response(200, headers={"content-type": "text/xml; charset=UTF-8"}, text=XML))
    res = await _server().call_tool("search_postings", {"query": "システム", "limit": 500, "page": 3})
    assert res.is_error is False, res.structured_content
    p = res.structured_content["postings"]
    assert [x["id"] for x in p] == ["ZnVrdXNoaW1hL3RhbXVyYV9jaXR5LzIwMjYK", "K2"]
    assert p[0]["title"] == "スタッドレスタイヤ購入" and p[0]["buyer"] == "福島県田村市"
    assert p[0]["url"] == "https://www.city.tamura.lg.jp/soshiki/3/assets/260930.pdf"
    assert p[0]["posted_at"] == "2026-09-04T00:00:00+09:00" and p[0]["deadline"] == "2026-09-29T00:00:00+09:00"
    assert p[0]["raw"]["Category"] == "物品" and p[0]["raw"]["Attachments"]["Attachment"]["Uri"] == "https://www.city.tamura.lg.jp/a.pdf"
    assert p[1]["buyer"] is None and p[1]["deadline"] is None
    q = route.calls.last.request.url.params
    assert q["Query"] == "システム" and q["Count"] == "100"  # capped at max_limit
    start = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}/", q["CFT_Issue_Date"]) and q["CFT_Issue_Date"][:10] in {start, (datetime.now(timezone.utc) - timedelta(days=61)).strftime("%Y-%m-%d")}
    assert set(q) == {"Query", "Count", "CFT_Issue_Date"}  # no paging parameter exists


@pytest.mark.asyncio
@respx.mock
async def test_an_api_error_document_yields_no_postings():
    respx.get(url__startswith=API).mock(return_value=httpx.Response(200, headers={"content-type": "text/xml"}, text="<Results><Error>Only one Kana character in search expression</Error></Results>"))
    res = await _server().call_tool("search_postings", {"query": "あ"})
    assert res.is_error is False and res.structured_content["postings"] == []


@pytest.mark.asyncio
@respx.mock
async def test_server_failure_is_an_is_error_result():
    respx.get(url__startswith=API).mock(return_value=httpx.Response(500, text="internal error"))
    res = await _server().call_tool("search_postings", {"query": "工事"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
