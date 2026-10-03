# GitLab.com (public projects, no token) MCP server

Category: **builder_tools** · Docs: https://docs.gitlab.com/api/projects/ · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/builder_tools/gitlab_public.json`; edit the catalog, not this file.

## Tools

- `list_items` — `GET /projects` (https://docs.gitlab.com/api/rest/#keyset-based-pagination)
- `get_item` — `GET /projects/{item_id}` (https://docs.gitlab.com/api/projects/#get-a-single-project)
- ~~`me`~~ not offered: No token in this public entry.
- ~~`generate_image`~~ not offered: Not an image service.
- ~~`generate_video`~~ not offered: Not a video service.
- ~~`get_job`~~ not offered: Not mapped.
- ~~`create_item`~~ not offered: Needs a token; public read entry only.
- ~~`update_item`~~ not offered: Needs a token; public read entry only.
- ~~`delete_item`~~ not offered: Needs a token; public read entry only.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve gitlab_public   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve gitlab_public
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve gitlab_public   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/gitlab_public-mcp`. Python and TypeScript serve identical tools.
