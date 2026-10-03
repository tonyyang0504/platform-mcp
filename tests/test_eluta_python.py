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

SPEC = json.loads((ROOT / "catalog" / "jobs" / "eluta.json").read_text(encoding="utf-8"))
FEED = 'https://www.eluta.ca/rss'
TWO = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:job_listing="https://example.invalid/job_listing" xmlns:wfw="http://wellformedweb.org/CommentAPI/"><channel><title>Feed</title><link>https://example.invalid/</link><item><title>Designer at Acme</title><link>https://www.eluta.ca/jobs/designer-1</link><description>We are hiring</description><pubDate>Thu, 24 Sep 2026 08:06:00 GMT</pubDate><guid>https://www.eluta.ca/jobs/designer-1</guid><employer>Teck Resources Limited</employer><location>Vancouver BC</location></item><item><title>Designer at Acme</title><link>https://www.eluta.ca/jobs/designer-19</link><description>We are hiring</description><pubDate>Thu, 24 Sep 2026 08:06:00 GMT</pubDate><guid>https://www.eluta.ca/jobs/designer-19</guid><employer>Teck Resources Limited</employer><location>Vancouver BC</location></item></channel></rss>'
ONE = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:job_listing="https://example.invalid/job_listing" xmlns:wfw="http://wellformedweb.org/CommentAPI/"><channel><title>Feed</title><link>https://example.invalid/</link><item><title>Designer at Acme</title><link>https://www.eluta.ca/jobs/designer-1</link><description>We are hiring</description><pubDate>Thu, 24 Sep 2026 08:06:00 GMT</pubDate><guid>https://www.eluta.ca/jobs/designer-1</guid><employer>Teck Resources Limited</employer><location>Vancouver BC</location></item></channel></rss>'
EXPECTED = {'id': 'https://www.eluta.ca/jobs/designer-1', 'title': 'Designer at Acme', 'url': 'https://www.eluta.ca/jobs/designer-1', 'posted_at': 'Thu, 24 Sep 2026 08:06:00 GMT', 'description': 'We are hiring', 'company': 'Teck Resources Limited', 'location': 'Vancouver BC'}
QUERY = {'q': 'design', 'l': 'Leeds'}


def _server():
    t = Transport(SPEC["adapter"]["base_url"], SPEC["adapter"]["auth"], {}, 50, "test")
    return build_server(SPEC, transport=t)


@pytest.mark.asyncio
async def test_only_the_keyless_feed_search_is_offered():
    tools = await _server().list_tools()
    assert [t.name for t in tools] == ["search"]
    assert tools[0].annotations.read_only_hint is True
    assert set(SPEC["adapter"]["not_offered"]) == {"me", "get_posting", "apply", "list_messages"}


@pytest.mark.asyncio
@respx.mock
async def test_search_parses_the_rss_feed_and_sends_the_documented_parameters():
    route = respx.get(url__startswith=FEED).mock(return_value=httpx.Response(200, headers={"content-type": "application/rss+xml; charset=utf-8"}, text=TWO))
    res = await _server().call_tool("search", {'query': 'design', 'location': 'Leeds', 'page': 2, 'limit': 5})
    assert res.is_error is False, res.structured_content
    posts = res.structured_content["postings"]
    assert len(posts) == 2
    for k, v in EXPECTED.items():
        assert posts[0].get(k) == v, k
    assert posts[0]["id"] != posts[1]["id"]
    req = route.calls.last.request
    assert str(req.url).split("?")[0] == FEED and req.method == "GET"
    assert dict(req.url.params) == QUERY
    assert "Authorization" not in req.headers


@pytest.mark.asyncio
@respx.mock
async def test_a_single_item_feed_is_still_a_list_and_an_empty_channel_is_empty():
    respx.get(url__startswith=FEED).mock(side_effect=[
        httpx.Response(200, headers={"content-type": "text/xml"}, text=ONE),
        httpx.Response(200, headers={"content-type": "text/xml"}, text='<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>')])
    one = await _server().call_tool("search", {"query": "x"})
    assert one.is_error is False and len(one.structured_content["postings"]) == 1
    empty = await _server().call_tool("search", {"query": "x"})
    assert empty.is_error is False and empty.structured_content["postings"] == []


@pytest.mark.asyncio
@respx.mock
async def test_an_unavailable_feed_is_an_is_error_result():
    respx.get(url__startswith=FEED).mock(return_value=httpx.Response(503, text="Service Unavailable"))
    res = await _server().call_tool("search", {"query": "design"})
    assert res.is_error is True and res.structured_content["error"] == "upstream_error"
