# GitHub (public search, no token) MCP server

Category: **builder_tools** · Docs: https://docs.github.com/en/rest/search/search · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/builder_tools/github_public.json`; edit the catalog, not this file.

## Tools

- `list_items` — `GET /search/{coll}` (https://docs.github.com/en/rest/search/search)
- `get_item` — `GET /{coll}/{item_id}` (https://docs.github.com/en/rest/repos/repos#get-a-repository)
- ~~`me`~~ not offered: No token in this public entry (GET /user needs one).
- ~~`generate_image`~~ not offered: Not an image service.
- ~~`generate_video`~~ not offered: Not a video service.
- ~~`get_job`~~ not offered: No jobs in this entry.
- ~~`create_item`~~ not offered: Creating issues or repositories needs a token; public read entry only.
- ~~`update_item`~~ not offered: Needs a token; public read entry only.
- ~~`delete_item`~~ not offered: Needs a token; public read entry only.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve github_public   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve github_public
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve github_public   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/github_public-mcp`. Python and TypeScript serve identical tools.
