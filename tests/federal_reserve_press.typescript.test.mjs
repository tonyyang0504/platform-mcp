import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("market_data", "federal_reserve_press");
const FEED = '﻿<?xml version="1.0" encoding="utf-8" ?><rss version="2.0"><channel><title>FRB</title><item><title>Stress test changes finalized</title><link><![CDATA[https://www.federalreserve.gov/a.htm]]></link><guid><![CDATA[https://www.federalreserve.gov/a.htm]]></guid><description><![CDATA[Board finalizes stress test changes]]></description><category>Banking</category><pubDate><![CDATA[Wed, 30 Sep 2026 13:00:00 GMT]]></pubDate></item><item><title>FOMC statement</title><link>https://www.federalreserve.gov/b.htm</link><guid>https://www.federalreserve.gov/b.htm</guid><description>Monetary policy</description><category>Monetary Policy</category><pubDate>Tue, 16 Sep 2026 18:00:00 GMT</pubDate></item></channel></rss>';

test("fed rss: RFC 822 dates as ISO, query and since filters (wire)", async () => {
  const { call } = await connect(SPEC, () => ({ body: FEED, type: "text/xml" }));
  const a = (await call("get_news", {})).structuredContent.articles;
  assert.deepEqual(a.map((x) => [x.title, x.published_at, x.source]), [["Stress test changes finalized", "2026-09-30T13:00:00Z", "Banking"], ["FOMC statement", "2026-09-16T18:00:00Z", "Monetary Policy"]]);
  assert.deepEqual((await call("get_news", { query: "monetary" })).structuredContent.articles.map((x) => x.title), ["FOMC statement"]);
  assert.deepEqual((await call("get_news", { since: "2026-09-30" })).structuredContent.articles.map((x) => x.title), ["Stress test changes finalized"]);
});
