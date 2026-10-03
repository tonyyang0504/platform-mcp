# Google Sheets / Drive MCP server

Category: **builder_tools** · Docs: https://developers.google.com/sheets/api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/builder_tools/google_sheets.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /spreadsheets/{spreadsheet_id}` (https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/get)
- `list_items` — `GET /spreadsheets/{spreadsheet_id}/values/{collection}` (https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/get)
- `get_item` — `GET /spreadsheets/{spreadsheet_id}/values/{item_id}` (https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/get)
- `create_item` — `POST /spreadsheets/{spreadsheet_id}/values/{collection}:append` (https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/append)
- `update_item` — `PUT /spreadsheets/{spreadsheet_id}/values/{item_id}` (https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/update)
- `delete_item` — `POST /spreadsheets/{spreadsheet_id}/values/{item_id}:clear` (https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/clear)
- ~~`generate_image`~~ not offered: Google Sheets has no generation endpoints.
- ~~`generate_video`~~ not offered: Google Sheets has no generation endpoints.
- ~~`get_job`~~ not offered: Sheets API calls are synchronous; there are no jobs.

## Credentials

- `PLATFORM_MCP_GOOGLE_SHEETS_CLIENT_ID` — OAuth 2.0 client id (Google Cloud console > Credentials) of a project with the Google Sheets API enabled.
- `PLATFORM_MCP_GOOGLE_SHEETS_CLIENT_SECRET` — The OAuth client's secret, sent in the form body of the refresh_token grant.
- `PLATFORM_MCP_GOOGLE_SHEETS_REFRESH_TOKEN` — Refresh token from Google's consent flow (offline access) with scope https://www.googleapis.com/auth/spreadsheets (or drive.file for files the app created); the runtime mints hourly access tokens from it.
- `PLATFORM_MCP_GOOGLE_SHEETS_SPREADSHEET_ID` — The spreadsheet id (the long id in https://docs.google.com/spreadsheets/d/<id>/edit) that every tool reads and writes.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve google_sheets   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve google_sheets
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve google_sheets   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/google_sheets-mcp`. Python and TypeScript serve identical tools.
