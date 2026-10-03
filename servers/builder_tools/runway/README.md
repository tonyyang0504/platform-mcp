# Runway MCP server

Category: **builder_tools** · Docs: https://docs.dev.runwayml.com · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/builder_tools/runway.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v1/organization` (https://docs.dev.runwayml.com/api/#tag/Organization/paths/~1v1~1organization/get)
- `generate_image` — `POST /v1/text_to_image` (https://docs.dev.runwayml.com/api/#tag/Start-generating/paths/~1v1~1text_to_image/post)
- `generate_video` — `POST /v1/text_to_video` (https://docs.dev.runwayml.com/api/#tag/Start-generating/paths/~1v1~1text_to_video/post)
- `get_job` — `GET /v1/tasks/{job_id}` (https://docs.dev.runwayml.com/api/#tag/Task-management/paths/~1v1~1tasks~1%7Bid%7D/get)
- `list_items` — `GET /v1/documents` (https://docs.dev.runwayml.com/api/#tag/Documents/paths/~1v1~1documents/get)
- `get_item` — `GET /v1/documents/{item_id}` (https://docs.dev.runwayml.com/api/#tag/Documents/paths/~1v1~1documents~1%7Bid%7D/get)
- `create_item` — `POST /v1/documents` (https://docs.dev.runwayml.com/api/#tag/Documents/paths/~1v1~1documents/post)
- `update_item` — `PATCH /v1/documents/{item_id}` (https://docs.dev.runwayml.com/api/#tag/Documents/paths/~1v1~1documents~1%7Bid%7D/patch)
- `delete_item` — `DELETE /v1/documents/{item_id}` (https://docs.dev.runwayml.com/api/#tag/Documents/paths/~1v1~1documents~1%7Bid%7D/delete)

## Credentials

- `PLATFORM_MCP_RUNWAY_API_KEY` — Runway API key (dev.runwayml.com > API keys), sent as Authorization: Bearer; every request also carries X-Runway-Version: 2024-11-06.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve runway   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve runway
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve runway   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/runway-mcp`. Python and TypeScript serve identical tools.
