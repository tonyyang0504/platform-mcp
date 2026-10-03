# AUTO.RIA MCP server

Category: **automotive** · Docs: https://docs-developers.ria.com/en/used-cars/auto_search_and_info/auto_info · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/automotive/autoria.json`; edit the catalog, not this file.

## Tools

- `get_listing` — `GET /auto/info` (https://docs-developers.ria.com/en/used-cars/auto_search_and_info/auto_info)
- `get_valuation` — `POST /auto/statistic-avarage-price/` (https://docs-developers.ria.com/en/used-cars/average_price/statistic_average_price)
- ~~`search_listings`~~ not offered: GET /auto/search returns only ad ids (search_result.ids is a list of strings) that each need an auto/info call; the runtime maps object rows only and does not fan out, so search is not served.
- ~~`decode_vin`~~ not offered: No VIN decoder in the AUTO.RIA API (VIN is only a search filter / ad field).
- ~~`list_dealers`~~ not offered: No dealer directory endpoint in the developers.ria.com used-cars reference.
- ~~`me`~~ not offered: No identity endpoint for an API key.

## Credentials

- `PLATFORM_MCP_AUTORIA_API_KEY` — Personal API key from the developers.ria.com cabinet (Особистий кабінет); sent as the api_key query parameter. auto/info is freemium, statistic-avarage-price is paid.
- `PLATFORM_MCP_AUTORIA_USER_ID` — Your RIA user id (integer); required by get_valuation (auto/statistic-avarage-price takes user_id and api_key in the query).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve autoria   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve autoria
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve autoria   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/autoria-mcp`. Python and TypeScript serve identical tools.
