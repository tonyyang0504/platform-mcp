import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("market_data", "arxiv_qfin");
const feed = (n, total) => `<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/" xmlns:arxiv="http://arxiv.org/schemas/atom"><opensearch:totalResults>${total}</opensearch:totalResults>` +
  Array.from({ length: n }, (_, i) => `<entry><id>http://arxiv.org/abs/2609.0000${i}v1</id><title>Paper ${i}</title><published>2026-09-29T15:48:47Z</published><link href="https://arxiv.org/abs/2609.0000${i}v1" rel="alternate" type="text/html"/><link href="https://arxiv.org/pdf/x" rel="related"/><arxiv:primary_category term="q-fin.TR" scheme="http://arxiv.org/schemas/atom"/></entry>`).join("") + "</feed>";

test("arxiv atom entries, total from opensearch, Error entry (wire)", async () => {
  let err = false;
  const { call, log } = await connect(SPEC, () => (err ? { body: '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Error</title><summary>start must be non-negative</summary></entry></feed>', type: "application/atom+xml" } : { body: feed(2, 3), type: "application/atom+xml" }));
  const r = (await call("get_news", { query: "market impact", limit: 2 })).structuredContent;
  assert.deepEqual(r.articles.map((a) => a.url), ["https://arxiv.org/abs/2609.00000v1", "https://arxiv.org/abs/2609.00001v1"]);
  assert.deepEqual([r.articles[0].source, r.total, r.next_page], ["q-fin.TR", 3, 2]);
  assert.equal(log[0].url.searchParams.get("search_query"), "cat:q-fin* AND all:market impact");
  err = true;
  const bad = (await call("get_news", { query: "x" })).structuredContent;
  assert.deepEqual([bad.error, bad.message], ["invalid_input", "start must be non-negative"]);
});
