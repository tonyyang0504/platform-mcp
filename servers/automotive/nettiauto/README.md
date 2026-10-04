# Nettiauto MCP server

Category: **automotive** · Docs: https://api.nettix.fi/docs/car/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/automotive/nettiauto.json`; edit the catalog, not this file.

## Tools

- `search_listings` — `GET /search` (https://api.nettix.fi/docs/car/#/Search)
- `get_listing` — `GET /ad/{listing_id}` (https://api.nettix.fi/docs/car/#/Car%20ad)
- ~~`decode_vin`~~ not offered: No VIN decoder in the Nettiauto REST API (vin is a search filter and ad field).
- ~~`get_valuation`~~ not offered: The pricing-tool schemas are not exposed as a documented read operation for arbitrary vehicles.
- ~~`list_dealers`~~ not offered: /my-dealers lists only the caller's own dealers, not a dealer directory.
- ~~`me`~~ not offered: No identity endpoint for a client-credentials token.

## Credentials

- `PLATFORM_MCP_NETTIAUTO_CLIENT_ID` — Nettix API client id (Alma Media grants API access to business customers on application); used with grant_type=client_credentials at https://auth.nettix.fi/oauth2/token.
- `PLATFORM_MCP_NETTIAUTO_CLIENT_SECRET` — The client's secret. The 24-hour JWT it mints is sent as the X-Access-Token header.

## Run

    uvx platform-mcp-hub serve nettiauto          # Python
    npx -y platform-mcp-hub serve nettiauto       # TypeScript
    claude mcp add nettiauto -- uvx platform-mcp-hub serve nettiauto

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/nettiauto-mcp`. Python and TypeScript serve identical tools.
