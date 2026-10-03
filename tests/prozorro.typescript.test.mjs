import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("deals", "prozorro");
const ROW = { id: "ca3fbd4f58f04aeb8298a7053be30664", tenderID: "UA-2026-09-11-013413-a", procuringEntity: { name: "Академія патрульної поліції" }, tenderPeriod: { startDate: "2026-09-11T17:31:09+03:00", endDate: "2026-09-28T17:33:16+03:00" } };

test("prozorro opaque offset cursor and titles from tender numbers (wire)", async () => {
  const { call, log } = await connect(SPEC, (u) => (u.pathname.endsWith("/tenders") ? { body: { data: [ROW], next_page: { offset: "1790861577.929.1.2ccf" } } } : { status: 404, body: { status: "error", errors: [{ description: "Not Found" }] } }));
  const r = (await call("search_postings", { limit: 1 })).structuredContent;
  assert.deepEqual([r.postings[0].title, r.next_cursor, r.next_page], ["UA-2026-09-11-013413-a", "1790861577.929.1.2ccf", null]);
  await call("search_postings", { limit: 1, cursor: "1790861577.929.1.2ccf" });
  assert.equal(log[1].url.searchParams.get("offset"), "1790861577.929.1.2ccf");
  assert.equal((await call("get_posting", { id: "nope" })).structuredContent.error, "not_found");
});
