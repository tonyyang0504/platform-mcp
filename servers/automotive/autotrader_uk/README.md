# Autotrader UK MCP server

Category: **automotive** · Docs: https://developers.autotrader.co.uk/api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/automotive/autotrader_uk.json`; edit the catalog, not this file.

## Tools

- `search_listings` — `GET /search` (https://developers.autotrader.co.uk/api#search-api)
- `get_listing` — `GET /search` (https://developers.autotrader.co.uk/api#search-api)
- `decode_vin` — `GET /vehicles` (https://developers.autotrader.co.uk/api#vehicles-api)
- `get_valuation` — `GET /vehicles` (https://developers.autotrader.co.uk/api#valuations)
- ~~`list_dealers`~~ not offered: The Advertisers API is a beta for configured advertisers only, not a public dealer directory.
- ~~`me`~~ not offered: No identity endpoint; the token only proves the key/secret pair.

## Credentials

- `PLATFORM_MCP_AUTOTRADER_UK_KEY` — Autotrader Connect API key (issued after Autotrader qualifies your integration; production and sandbox keys differ); POSTed form-encoded to https://api.autotrader.co.uk/authenticate.
- `PLATFORM_MCP_AUTOTRADER_UK_SECRET` — The matching API secret. Access tokens last 15 minutes and are re-minted on expiry or 401; unused credentials are removed after 90 days.
- `PLATFORM_MCP_AUTOTRADER_UK_ADVERTISER_ID` — Autotrader advertiser id your credentials are permitted for (sent as advertiserId on every call, as in all documented examples).

## Run

    uvx platform-mcp-hub serve autotrader_uk          # Python
    npx -y platform-mcp-hub serve autotrader_uk       # TypeScript
    claude mcp add autotrader_uk -- uvx platform-mcp-hub serve autotrader_uk

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/autotrader_uk-mcp`. Python and TypeScript serve identical tools.
