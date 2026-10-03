# Zalora MCP server

Category: **ecommerce_channels** · Docs: https://sellercenter-api.zalora.com/docs/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/zalora.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/seller-settings` (https://sellercenter-api.zalora.com/docs/openapi-standalone.yaml)
- `update_listing` — `PUT /v2/product/{listing_id}/prices/{country}` (https://sellercenter-api.zalora.com/docs/openapi-standalone.yaml)
- `set_inventory` — `PUT /v2/stock/product` (https://sellercenter-api.zalora.com/docs/openapi-standalone.yaml)
- `end_listing` — `PUT /v2/product/{listing_id}/prices/{country}/status` (https://sellercenter-api.zalora.com/docs/openapi-standalone.yaml)
- `list_orders` — `GET /v2/orders` (https://sellercenter-api.zalora.com/docs/openapi-standalone.yaml)
- ~~`create_listing`~~ not offered: POST /v2/product-set needs a category/attribute-set specific payload (brand, attributes, variations with seller SKUs; see /v2/product-sets/sample-payload/{categoryId}); the vocabulary has no category or brand.
- ~~`mark_shipped`~~ not offered: POST /v2/orders/statuses/set-to-shipped and /v2/order-item/{orderItemId}/tracking-code act on ORDER ITEM ids (orderItemIds), not on an order id; order item ids are not vocabulary inputs.

## Credentials

- `PLATFORM_MCP_ZALORA_CLIENT_ID` — Application ID of an OAuth application created in ZALORA Seller Center (Settings > Integration Management > OAuth Applications > Add Application).
- `PLATFORM_MCP_ZALORA_CLIENT_SECRET` — Application Secret of the same application; sent with the id as HTTP Basic to /oauth/client-credentials (grant_type=client_credentials) for a 1-hour bearer token.
- `PLATFORM_MCP_ZALORA_COUNTRY` — Country code of the price row that update_listing / end_listing change (Seller Center country code of the venture, as used in PUT /v2/product/{productId}/prices/{country}).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve zalora   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve zalora
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve zalora   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/zalora-mcp`. Python and TypeScript serve identical tools.
