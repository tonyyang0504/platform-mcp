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

SPEC = json.loads((ROOT / "catalog" / "deals" / "service_bund_de.json").read_text(encoding="utf-8"))
FEED = 'https://www.service.bund.de/Content/DE/Ausschreibungen/Suche/Formular.html'
XML = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Feed</title><link>https://example.invalid/</link><item><title>Software für die Friedhofsverwaltung</title><link>https://www.service.bund.de/IMPORTE/Ausschreibungen/editor/Stadt-X/2026/09/6649990.html#track=feed-callforbids</link><description><![CDATA[Erfüllungsort: <strong>Leipzig</strong><br />Vergabestelle: <strong>Stadt Leipzig</strong><br />Angebotsfrist: <strong>13.10.2026 10:00</strong>]]></description><pubDate>Fri, 25 Sep 2026 07:00:00 +0200</pubDate><guid>https://www.service.bund.de/IMPORTE/Ausschreibungen/editor/Stadt-X/2026/09/6649990.html</guid></item><item><title>Reinigung</title><link>https://www.service.bund.de/IMPORTE/Ausschreibungen/a.html</link><description>x</description><pubDate>Thu, 24 Sep 2026 07:00:00 +0200</pubDate><guid>https://www.service.bund.de/IMPORTE/Ausschreibungen/a.html</guid></item></channel></rss>'
ONE = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Feed</title><link>https://example.invalid/</link><item><title>Reinigung</title><link>https://www.service.bund.de/IMPORTE/Ausschreibungen/a.html</link><description>x</description><pubDate>Thu, 24 Sep 2026 07:00:00 +0200</pubDate><guid>https://www.service.bund.de/IMPORTE/Ausschreibungen/a.html</guid></item></channel></rss>'



def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_the_feed_search_is_offered():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search_postings"]
    assert tools[0].annotations.read_only_hint is True
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "get_posting", "submit_bid", "withdraw_bid", "bid_status", "list_messages", "send_message", "credits"}


@pytest.mark.asyncio
@respx.mock
async def test_search_parses_the_rss_feed_and_maps_items():
    route = respx.get(url__startswith=FEED).mock(return_value=httpx.Response(200, headers={"content-type": "application/rss+xml; charset=utf-8"}, text=XML))
    res = await _server().call_tool("search_postings", {'query': 'Software', 'page': 1})
    assert res.is_error is False, res.structured_content
    posts = res.structured_content["postings"]
    assert len(posts) == 2
    for k, v in {'id': 'https://www.service.bund.de/IMPORTE/Ausschreibungen/editor/Stadt-X/2026/09/6649990.html', 'title': 'Software für die Friedhofsverwaltung', 'url': 'https://www.service.bund.de/IMPORTE/Ausschreibungen/editor/Stadt-X/2026/09/6649990.html#track=feed-callforbids', 'posted_at': 'Fri, 25 Sep 2026 07:00:00 +0200'}.items():
        assert posts[0][k] == v, k
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == FEED and req.method == "GET"
    assert dict(req.url.params) == {'templateQueryString': 'Software', 'nn': '4641482', 'resultsPerPage': '100', 'sortOrder': 'dateOfIssue_dt desc', 'jobsrss': 'true'}  # the feed documents no search/paging parameters beyond these
    assert "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_a_single_item_feed_is_still_a_list():
    respx.get(url__startswith=FEED).mock(return_value=httpx.Response(200, headers={"content-type": "text/xml"}, text=ONE))
    res = await _server().call_tool("search_postings", {})
    assert res.is_error is False and len(res.structured_content["postings"]) == 1


@pytest.mark.asyncio
@respx.mock
async def test_an_empty_channel_and_a_blocked_feed():
    respx.get(url__startswith=FEED).mock(side_effect=[
        httpx.Response(200, headers={"content-type": "application/rss+xml"}, text='<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>'),
        httpx.Response(503, text="Service Unavailable")])
    empty = await _server().call_tool("search_postings", {})
    assert empty.is_error is False and empty.structured_content["postings"] == [] and empty.structured_content["next_page"] is None
    res = await _server().call_tool("search_postings", {})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
