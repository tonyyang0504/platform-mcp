# Magalu Marketplace MCP server

Category: **ecommerce_channels** · Docs: https://developers.magalu.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/magalu.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /seller/v1/portfolios/me` (https://developers.magalu.com/apis/products.openapi.yaml)
- `set_inventory` — `PATCH /seller/v1/portfolios/stocks/{sku}` (https://developers.magalu.com/apis/products.openapi.yaml)
- `end_listing` — `PATCH /seller/v1/portfolios/skus/{listing_id}` (https://developers.magalu.com/apis/products.openapi.yaml)
- `list_orders` — `GET /seller/v1/orders` (https://developers.magalu.com/apis/orders.openapi.yaml)
- ~~`create_listing`~~ not offered: POST /seller/v1/portfolios/skus needs category, brand, condition, dimensions, images and fiscal data (ncm, origin), and prices are created separately; the vocabulary lacks category, brand and dimensions.
- ~~`update_listing`~~ not offered: Prices (PATCH /seller/v1/portfolios/prices/{sku}) are integers with a normalizer (price 1999 + normalizer 100 = 19.99) plus channel and currency; converting the vocabulary's decimal price needs arithmetic the adapter lacks, and a text-only SKU patch would leave the declared price unchanged.
- ~~`mark_shipped`~~ not offered: Shipping is per delivery: POST /seller/v1/deliveries/{id}/shippings after an NF-e is attached (/deliveries/{id}/invoices); the delivery id and invoice are not vocabulary inputs.

## Credentials

- `PLATFORM_MCP_MAGALU_CLIENT_ID` — Client ID of your application created with the ID Magalu CLI (see developers.magalu.com > Primeiros passos > Criar aplicação).
- `PLATFORM_MCP_MAGALU_CLIENT_SECRET` — Client secret of the same application.
- `PLATFORM_MCP_MAGALU_REFRESH_TOKEN` — Refresh token from a one-time authorization-code consent of the seller at https://id.magalu.com (scopes such as open:portfolio:read/write, open:order-order:read). If ID Magalu returns a new refresh token on refresh, the runtime keeps it (and saves it with PLATFORM_MCP_STATE_DIR).
- `PLATFORM_MCP_MAGALU_CHANNEL_ID` — Sales channel id the stock applies to (GET /seller/v1/portfolios/me returns channel.id).

## Run

    uvx platform-mcp-hub serve magalu          # Python
    npx -y platform-mcp-hub serve magalu       # TypeScript
    claude mcp add magalu -- uvx platform-mcp-hub serve magalu

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/magalu-mcp`. Python and TypeScript serve identical tools.
