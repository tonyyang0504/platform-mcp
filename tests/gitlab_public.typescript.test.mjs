import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";
import { fromHeaders, parseLinkHeader } from "../runtime/typescript/dist/adapter.js";

const SPEC = loadSpec("builder_tools", "gitlab_public");
const LINK = '<https://gitlab.com/api/v4/projects?id_after=89655&order_by=id&pagination=keyset&per_page=2&search=mcp&sort=asc>; rel="next"';

test("link header parsing is the same as Python's", () => {
  assert.deepEqual(parseLinkHeader('<https://x/?page=3>; rel="next", <https://x/?page=1>; rel="prev first", <https://x/?page=9>; rel=last'),
    { next: "https://x/?page=3", prev: "https://x/?page=1", first: "https://x/?page=1", last: "https://x/?page=9" });
  assert.equal(fromHeaders("link:page", { link: '<https://x/?page=3>; rel="next"' }), "3");
  assert.equal(fromHeaders("link:page", {}), null);
  assert.equal(fromHeaders("header:X-Total", { "x-total": "42" }), "42");
});

test("gitlab keyset cursor from the Link header (wire)", async () => {
  const { call, log } = await connect(SPEC, (u) => (u.searchParams.get("id_after")
    ? { body: [{ id: 90000, path_with_namespace: "c/mcp3", web_url: "https://gitlab.com/c/mcp3" }] }
    : { body: [{ id: 22269, path_with_namespace: "a/mcp1" }, { id: 89655, path_with_namespace: "b/mcp2" }], headers: { link: LINK } }));
  const p1 = (await call("list_items", { query: "mcp", limit: 2 })).structuredContent;
  assert.deepEqual([p1.items.map((i) => i.id), p1.next_cursor, p1.next_page], [["22269", "89655"], "89655", null]);
  const p2 = (await call("list_items", { query: "mcp", limit: 2, cursor: "89655" })).structuredContent;
  assert.deepEqual([p2.items.map((i) => i.id), p2.next_cursor], [["90000"], null]);
  assert.equal(log[1].url.searchParams.get("id_after"), "89655");
});
