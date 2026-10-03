"""Federal Reserve press releases (forge stress test 2026-10, RSS 2.0 with a BOM): RFC 822 dates as ISO (isodate: %a %b),
query and since filters on a feed with no paging."""
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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "federal_reserve_press.json").read_text(encoding="utf-8"))
URL = "https://www.federalreserve.gov/feeds/press_all.xml"
FEED = ('﻿<?xml version="1.0" encoding="utf-8" ?><rss version="2.0"><channel><title>FRB: Press Release - All Releases</title>'
        '<item><title>Stress test changes finalized</title><link><![CDATA[https://www.federalreserve.gov/a.htm]]></link><guid><![CDATA[https://www.federalreserve.gov/a.htm]]></guid>'
        '<description><![CDATA[Board finalizes stress test changes]]></description><category>Banking</category><pubDate><![CDATA[Wed, 30 Sep 2026 13:00:00 GMT]]></pubDate></item>'
        '<item><title>FOMC statement</title><link>https://www.federalreserve.gov/b.htm</link><guid>https://www.federalreserve.gov/b.htm</guid>'
        '<description>Monetary policy</description><category>Monetary Policy</category><pubDate>Tue, 16 Sep 2026 18:00:00 GMT</pubDate></item></channel></rss>')


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_rss_items_dates_and_filters():
    respx.get(URL).mock(return_value=httpx.Response(200, headers={"content-type": "text/xml"}, content=FEED.encode("utf-8")))
    a = (await _server().call_tool("get_news", {})).structured_content["articles"]
    assert [(x["title"], x["published_at"], x["source"]) for x in a] == [("Stress test changes finalized", "2026-09-30T13:00:00Z", "Banking"), ("FOMC statement", "2026-09-16T18:00:00Z", "Monetary Policy")]
    assert a[0]["id"] == a[0]["url"] == "https://www.federalreserve.gov/a.htm"
    assert [x["title"] for x in (await _server().call_tool("get_news", {"query": "monetary"})).structured_content["articles"]] == ["FOMC statement"]
    assert [x["title"] for x in (await _server().call_tool("get_news", {"since": "2026-09-30"})).structured_content["articles"]] == ["Stress test changes finalized"]
