# Webflow MCP server

Category: **builder_tools** · Docs: https://developers.webflow.com/data/reference · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/builder_tools/webflow.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /token/authorized_by` (https://developers.webflow.com/data/reference/token/authorized-by)
- `list_items` — `GET /collections/{collection}/items` (https://developers.webflow.com/data/reference/cms/collection-items/staged-items/list-items)
- `get_item` — `GET /collections/{collection}/items/{item_id}` (https://developers.webflow.com/data/reference/cms/collection-items/staged-items/get-item)
- `create_item` — `POST /collections/{collection}/items` (https://developers.webflow.com/data/reference/cms/collection-items/staged-items/create-item)
- `update_item` — `PATCH /collections/{collection}/items/{item_id}` (https://developers.webflow.com/data/reference/cms/collection-items/staged-items/update-item)
- `delete_item` — `DELETE /collections/{collection}/items/{item_id}` (https://developers.webflow.com/data/reference/cms/collection-items/staged-items/delete-item)
- ~~`generate_image`~~ not offered: Webflow's Data API has no generation endpoints.
- ~~`generate_video`~~ not offered: Webflow's Data API has no generation endpoints.
- ~~`get_job`~~ not offered: No generation jobs in the Data API.

## Credentials

- `PLATFORM_MCP_WEBFLOW_TOKEN` — Webflow site API token (Site settings > Apps & integrations > API access) or OAuth access token with CMS:read/CMS:write (and authorized_user:read for me).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve webflow   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve webflow
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve webflow   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/webflow-mcp`. Python and TypeScript serve identical tools.
