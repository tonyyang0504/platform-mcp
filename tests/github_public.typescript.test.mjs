import assert from "node:assert/strict";
import { test } from "node:test";
import { connect, loadSpec } from "./lib/harness.mjs";

const SPEC = loadSpec("builder_tools", "github_public");

test("github search, owner/repo get, 403 rate limit and refused traversal (wire)", async () => {
  const { call, log } = await connect(SPEC, (u) => {
    if (u.pathname === "/search/repositories") return { body: { total_count: 3, items: [{ full_name: "modelcontextprotocol/servers", html_url: "https://github.com/modelcontextprotocol/servers" }, { full_name: "a/b", html_url: "https://github.com/a/b" }] } };
    if (u.pathname === "/repos/modelcontextprotocol/servers") return { body: { full_name: "modelcontextprotocol/servers", description: "Model Context Protocol Servers" } };
    return { status: 403, body: { message: "API rate limit exceeded for 1.2.3.4." } };
  });
  const r = (await call("list_items", { collection: "repositories", query: "mcp server", limit: 2 })).structuredContent;
  assert.deepEqual([r.items.map((i) => i.id), r.total, r.next_page], [["modelcontextprotocol/servers", "a/b"], 3, 2]);
  assert.equal(log[0].url.searchParams.get("q"), "mcp server");
  assert.equal((await call("get_item", { collection: "repositories", item_id: "modelcontextprotocol/servers" })).structuredContent.content, "Model Context Protocol Servers");
  assert.equal((await call("list_items", { collection: "users", query: "tony" })).structuredContent.error, "rate_limited");
  assert.equal((await call("get_item", { collection: "users", item_id: "../user/emails" })).structuredContent.error, "invalid_input");
  assert.equal(log.length, 3);
});
