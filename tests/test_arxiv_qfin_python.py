"""arXiv q-fin (forge stress test 2026-10, Atom 1.0): offset paging with an OpenSearch total (an XML string), Atom
links as attributes, errors as a 200 feed whose only entry is titled 'Error'."""
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

SPEC = json.loads((ROOT / "catalog" / "market_data" / "arxiv_qfin.json").read_text(encoding="utf-8"))
URL = "https://export.arxiv.org/api/query"


def _feed(n: int, total: int) -> str:
    entries = "".join(f'<entry><id>http://arxiv.org/abs/2609.{i:05d}v1</id><title>Paper {i}</title><published>2026-09-29T15:48:47Z</published>'
                      f'<link href="https://arxiv.org/abs/2609.{i:05d}v1" rel="alternate" type="text/html"/><link href="https://arxiv.org/pdf/x" rel="related"/>'
                      f'<arxiv:primary_category term="q-fin.TR" scheme="http://arxiv.org/schemas/atom"/></entry>' for i in range(n))
    return (f'<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/" '
            f'xmlns:arxiv="http://arxiv.org/schemas/atom"><opensearch:totalResults>{total}</opensearch:totalResults>{entries}</feed>')


def _server():
    a = SPEC["adapter"]
    return build_server(SPEC, transport=Transport(a["base_url"], a["auth"], {}, 50, "test", envelope=a.get("envelope")))


@pytest.mark.asyncio
@respx.mock
async def test_atom_entries_paging_and_total():
    route = respx.get(URL).mock(return_value=httpx.Response(200, headers={"content-type": "application/atom+xml"}, text=_feed(2, 3)))
    r = (await _server().call_tool("get_news", {"query": "market impact", "limit": 2, "page": 1})).structured_content
    assert [a["url"] for a in r["articles"]] == ["https://arxiv.org/abs/2609.00000v1", "https://arxiv.org/abs/2609.00001v1"]
    assert r["articles"][0]["source"] == "q-fin.TR" and r["total"] == 3 and r["next_page"] == 2
    q = route.calls.last.request.url.params
    assert (q["search_query"], q["start"], q["max_results"]) == ("cat:q-fin* AND all:market impact", "0", "2")
    await _server().call_tool("get_news", {"limit": 2, "page": 2})
    assert route.calls.last.request.url.params["search_query"] == "cat:q-fin*" and route.calls.last.request.url.params["start"] == "2"


@pytest.mark.asyncio
@respx.mock
async def test_error_entry():
    respx.get(URL).mock(return_value=httpx.Response(200, headers={"content-type": "application/atom+xml"}, text=(
        '<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><id>https://arxiv.org/api/errors#start</id>'
        '<title>Error</title><summary>start must be non-negative</summary></entry></feed>')))
    r = await _server().call_tool("get_news", {"query": "x"})
    assert r.is_error and r.structured_content["error"] == "invalid_input" and r.structured_content["message"] == "start must be non-negative"
