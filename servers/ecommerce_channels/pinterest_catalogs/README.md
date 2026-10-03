# Pinterest Catalogs MCP server

Category: **ecommerce_channels** · Docs: https://developers.pinterest.com/docs/api/v5/catalogs-list/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/pinterest_catalogs.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /user_account` (https://developers.pinterest.com/docs/api/v5/#operation/user_account/get)
- `update_listing` — `POST /catalogs/items/batch` (https://developers.pinterest.com/docs/api/v5/#operation/items_batch/post)
- `end_listing` — `POST /catalogs/items/batch` (https://developers.pinterest.com/docs/api/v5/#operation/items_batch/post)
- ~~`create_listing`~~ not offered: A RETAIL item CREATE requires link, image_link, availability, condition and google_product_category-style attributes besides title/price, and CREATE/UPSERT is restricted for merchants with a feed data source; the vocabulary has no product link.
- ~~`set_inventory`~~ not offered: Pinterest catalog items carry an availability state ('in stock' | 'out of stock' | 'preorder'), not a stock quantity.
- ~~`list_orders`~~ not offered: Pinterest catalogs have no orders; checkout happens on the merchant's site.
- ~~`mark_shipped`~~ not offered: No orders or shipments in the Pinterest API.

## Credentials

- `PLATFORM_MCP_PINTEREST_CATALOGS_CLIENT_ID` — Pinterest app id; HTTP Basic username on POST https://api.pinterest.com/v5/oauth/token.
- `PLATFORM_MCP_PINTEREST_CATALOGS_CLIENT_SECRET` — Pinterest app secret key; HTTP Basic password on the token request.
- `PLATFORM_MCP_PINTEREST_CATALOGS_REFRESH_TOKEN` — Refresh token from the authorization-code flow with scopes user_accounts:read, catalogs:read and catalogs:write (apps have trial access until Pinterest grants standard access). Continuous refresh tokens rotate on every refresh: the runtime keeps the new one and, with PLATFORM_MCP_STATE_DIR set, saves it to <dir>/pinterest_catalogs.json (0600).
- `PLATFORM_MCP_PINTEREST_CATALOGS_COUNTRY` — Two-letter country of the catalog items, e.g. US.
- `PLATFORM_MCP_PINTEREST_CATALOGS_LANGUAGE` — Language of the catalog items, e.g. en-US or EN.
- `PLATFORM_MCP_PINTEREST_CATALOGS_CURRENCY` — ISO currency appended to prices ('24.99 USD'); required when update_listing sends a price.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve pinterest_catalogs   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve pinterest_catalogs
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve pinterest_catalogs   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/pinterest_catalogs-mcp`. Python and TypeScript serve identical tools.
